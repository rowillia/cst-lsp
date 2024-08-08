from collections import defaultdict
from collections.abc import Sequence
from dataclasses import astuple, dataclass, field

import libcst as cst
from libcst.metadata import (
    CodeRange,
    PositionProvider,
)
from lsprotocol import types as lsp_types

from .base import BaseCstLspCodeAction
from .variable_collector import VariableCollector


@dataclass(frozen=True)
class ExtractMethodConfig:
    new_func_name: str
    start_line: int
    end_line: int


@dataclass
class ParserState:
    target_function_node: cst.FunctionDef | None = None
    lowest_indented_block: cst.IndentedBlock | None = None
    variable_collector: VariableCollector = field(default_factory=VariableCollector)
    new_function_def: cst.FunctionDef | None = None
    contains_return: bool = False
    contains_await: bool = False
    contains_yield: bool = False
    is_classmethod: bool = False
    is_staticmethod: bool = False
    current_scope: list[cst.CSTNode] = field(default_factory=list)
    added_new_function: bool = False


@dataclass
class NewFunctionInformation:
    receiver_name: str | None
    decorators: list[cst.Decorator]
    callsite_params: list[str]
    declaration_params: list[str]
    return_vars: list[str]
    return_type: cst.Annotation | None


class FunctionExtractor(cst.CSTTransformer):
    """
    Extracts a selection of code into a new function and replaces
    the original code with a call to that function.

    Known problems:
        - Handling other control flow statements
            - continue
            - break
            - yield
            - yield from
        - Handling module-level code (e.g. not within a function)
        - Not all branches return, for example:
                if x == 3:
                    return 42
                y = 3
    """

    METADATA_DEPENDENCIES = (PositionProvider,)

    def __init__(self, config: ExtractMethodConfig):
        super().__init__()
        self.config = config
        self.state = ParserState()

    def position_for_node(self, node: cst.CSTNode) -> CodeRange:
        position = self.get_metadata(PositionProvider, node)
        assert isinstance(position, CodeRange)
        return position

    def is_node_in_range(self, node: cst.CSTNode) -> bool:
        position = self.position_for_node(node)
        return (
            (self.config.start_line <= position.start.line <= self.config.end_line)
            or (self.config.start_line <= position.end.line <= self.config.end_line)
            or (position.start.line <= self.config.start_line <= position.end.line)
            or (position.start.line <= self.config.end_line <= position.end.line)
        )

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:
        # Keep track of the stack of classes to properly handle
        # staticmethod and classmethod when extracting methods
        self.state.current_scope.append(node)
        return True

    def leave_ClassDef(
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        self.state.current_scope.pop()
        return updated_node

    @staticmethod
    def _analyze_decorators(decorators: Sequence[cst.Decorator]) -> tuple[bool, bool]:
        is_staticmethod = False
        is_classmethod = False
        for decorator in decorators:
            if isinstance(decorator.decorator, cst.Name):
                if decorator.decorator.value == "staticmethod":
                    is_staticmethod = True
                elif decorator.decorator.value == "classmethod":
                    is_classmethod = True
        return is_staticmethod, is_classmethod

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:
        self.state.current_scope.append(node)
        if self.is_node_in_range(node):
            self.state.target_function_node = node
            self.state.variable_collector.metadata = self.metadata
            node.visit(self.state.variable_collector)
        return True

    def leave_Module(
        self, original_node: cst.Module, updated_node: cst.Module
    ) -> cst.Module:
        # If we weren't able to add in the new function abort the refactor
        # instead of leaving the code in a bad state.
        if self.state.added_new_function:
            return updated_node
        else:
            return original_node

    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef | cst.FlattenSentinel:
        self.state.current_scope.pop()

        if original_node != self.state.target_function_node:
            return updated_node

        self.state.target_function_node = None
        if self.state.new_function_def is None:
            # We were unable to create the new function
            # for some reason.  Bail on the refactoring.
            return updated_node

        self.state.new_function_def = self.state.new_function_def.with_changes(
            leading_lines=updated_node.leading_lines
        )
        if not updated_node.leading_lines:
            updated_node = updated_node.with_changes(
                leading_lines=[cst.EmptyLine(indent=False)]
            )
        body_statements = [
            self.state.new_function_def,
            updated_node,
        ]
        self.state.added_new_function = True
        return cst.FlattenSentinel(body_statements)

    def visit_IndentedBlock(self, node: cst.IndentedBlock) -> bool:
        position = self.position_for_node(node)
        if (
            position.start.line <= self.config.start_line
            and position.end.line >= self.config.end_line
        ):
            self.state.lowest_indented_block = node
        return True

    def visit_Return(self, node: cst.Return) -> bool:
        # Track whether or not the code contained within the requested
        # refactor contains a return.  If it does, the extracted
        # function has to have the same return type as the parent.
        # We also need to know if it contains a return so we can have the
        # refactor also return.
        # This doesn't do anything akin to escape analysis to ensure all
        # codepaths still return.
        if self.is_node_in_range(node):
            self.state.contains_return = True
        return True

    def visit_Yield(self, node: cst.Yield) -> bool:
        if self.is_node_in_range(node):
            self.state.contains_yield = True
        return True

    def visit_Await(self, node: cst.Await) -> bool:
        # Track whether the code within the refactor contains an await statement.
        # If it does, the extracted function needs to be async and the call to it
        # needs to be awaited.
        if self.is_node_in_range(node):
            self.state.contains_await = True
        return True

    def leave_IndentedBlock(
        self, original_node: cst.IndentedBlock, updated_node: cst.IndentedBlock
    ):
        """
        If we've found the lowest indented block that contains all of the code
        to be pulled out, do the refactor and store the new function definition
        so it can be added in later.
        """
        if original_node is not self.state.lowest_indented_block:
            return updated_node

        self.state.lowest_indented_block = None

        call_info = self.compute_call_information()
        new_updated_node, new_func_body = self.split_original_code(
            original_node, call_info
        )

        if not new_func_body:
            # If we didn't find any lines we can validly extract
            # then don't attempt to refactor.  This can happen when trying
            # to extract a series of paramters into a function, for example:
            #
            # some_func(
            #     a = foo,
            #     b = bar
            # )
            #
            # While `a = foo` is a valid statement, we don't yet support
            # refactoring it out of the parameters.
            return updated_node
        else:
            updated_node = new_updated_node

        new_func = self.create_new_function(
            call_info,
            new_func_body,
        )
        self.state.new_function_def = new_func
        return updated_node

    def analyze_variables(self) -> tuple[list[str], list[str]]:
        """Tracks where variables are accessed.

        Variables assigned before the refactored code and accessed within it
        have to be passed in as parameters.  Variables assigned during the
        refactored code that are then accessed after the refactored code must
        be returned.
        """
        assignments_before = defaultdict(set)
        assignments_during = defaultdict(set)
        usage_during = defaultdict(set)
        usage_after = defaultdict(set)

        for var, positions in self.state.variable_collector.assignments.items():
            for pos in positions:
                if pos.line < self.config.start_line:
                    assignments_before[var].add(astuple(pos))
                elif pos.line <= self.config.end_line:
                    assignments_during[var].add(astuple(pos))

        for var, positions in self.state.variable_collector.usages.items():
            for pos in positions:
                if pos.line > self.config.end_line:
                    usage_after[var].add(astuple(pos))
                elif pos.line >= self.config.start_line:
                    usage_during[var].add(astuple(pos))

        return_vars = [x for x in assignments_during.keys() if x in usage_after]
        params = sorted(
            [x for x in usage_during.keys() if x in assignments_before],
            key=lambda x: min(assignments_before[x]),
        )
        return return_vars, params

    def get_return_type(self, return_vars: list[str]) -> cst.Annotation | None:
        """Creates the return type for the new function.

        If the function we're extracting a method from contains a return type and the
        code being pulled out returns, use that return type.  Otherwise try to infer
        it from the variables being returned.
        """
        if self.state.contains_return:
            return (
                self.state.target_function_node.returns
                if self.state.target_function_node
                else None
            )
        if not return_vars:
            return None
        if len(return_vars) == 1:
            annotation = self.state.variable_collector.types.get(return_vars[0], None)
            return (
                annotation.with_changes(
                    whitespace_before_indicator=cst.SimpleWhitespace(" ")
                )
                if annotation
                else None
            )
        # If multiple variables are being returned and _all_ of them are typed,
        # specify the return type, otherwise leave the function untyped.
        if all(var in self.state.variable_collector.types for var in return_vars):
            return cst.Annotation(
                annotation=cst.Subscript(
                    value=cst.Name("tuple"),
                    slice=[
                        cst.SubscriptElement(
                            cst.Index(
                                self.state.variable_collector.types[var].annotation
                            )
                        )
                        for var in return_vars
                    ],
                ),
                whitespace_before_indicator=cst.SimpleWhitespace(" "),
            )
        return None

    def compute_call_information(self) -> NewFunctionInformation:
        # The reciever may vary based on the current's function's context.
        # For example, if we're within an instance method the reciever will
        # be the first parameter of the function (typically `self`).  If we're
        # within a staticmethod, it will be the classname.
        receiver_name: str | None = None
        decorators = []

        return_vars, params = self.analyze_variables()
        return_type = self.get_return_type(return_vars)

        # We have to split out the `callsite_params` from the `declaration`
        # params as they may differ.  For example, an instance method
        # on a class will be declared `def foo(self, bar)` but will be
        # invoked with `self.foo(bar)`
        callsite_params = params.copy()
        declaration_params = params.copy()

        parent_function = (
            self.state.current_scope[-1]
            if self.state.current_scope
            and isinstance(self.state.current_scope[-1], cst.FunctionDef)
            else None
        )
        if parent_function:
            grandparent = (
                len(self.state.current_scope) >= 2 and self.state.current_scope[-2]
            )

            if isinstance(grandparent, cst.ClassDef):
                is_staticmethod, is_classmethod = self._analyze_decorators(
                    parent_function.decorators
                )
                if is_staticmethod:
                    decorators.append(cst.Decorator(decorator=cst.Name("staticmethod")))
                    receiver_name = grandparent.name.value

                else:
                    receiver_name = (
                        parent_function.params.params[0].name.value
                        if parent_function.params.params
                        else None
                    )

                    if is_classmethod:
                        decorators.append(
                            cst.Decorator(decorator=cst.Name("classmethod"))
                        )

                    if receiver_name:
                        if receiver_name in params:
                            callsite_params.remove(receiver_name)
                            declaration_params.remove(receiver_name)
                        declaration_params.insert(0, receiver_name)

        return NewFunctionInformation(
            receiver_name=receiver_name,
            decorators=decorators,
            callsite_params=callsite_params,
            declaration_params=declaration_params,
            return_vars=return_vars,
            return_type=return_type,
        )

    def create_new_function(
        self,
        call_info: NewFunctionInformation,
        new_func_body,
    ) -> cst.FunctionDef:
        new_params = [
            cst.Param(
                name=cst.Name(param),
                annotation=self.state.variable_collector.types.get(param, None),
            )
            for param in call_info.declaration_params
        ]

        if self.state.contains_yield:
            # We'll skip adding a return annotation for now
            return_annotation = None
        else:
            return_annotation = call_info.return_type

        if not self.state.contains_return and call_info.return_vars:
            return_stmt = self.create_return_statement(call_info.return_vars)
            new_func_body.append(cst.SimpleStatementLine(body=[return_stmt]))

        return cst.FunctionDef(
            name=cst.Name(self.config.new_func_name),
            params=cst.Parameters(params=new_params),
            body=cst.IndentedBlock(body=new_func_body),
            returns=return_annotation,
            decorators=call_info.decorators,
            asynchronous=cst.Asynchronous() if self.state.contains_await else None,
        )

    def create_return_statement(self, return_vars: list[str]) -> cst.Return:
        if len(return_vars) > 1:
            return cst.Return(
                cst.Tuple(
                    [cst.Element(cst.Name(var)) for var in return_vars],
                    lpar=[],
                    rpar=[],
                )
            )
        else:
            return cst.Return(cst.Name(return_vars[0]))

    def split_original_code(
        self,
        original_node: cst.IndentedBlock,
        call_info: NewFunctionInformation,
    ) -> tuple[cst.IndentedBlock, list[cst.BaseStatement]]:
        """
        Split the original code out of the original indented block and into a list of statements.

        Args:
            original_node (cst.IndentedBlock): The original indented block of code.
            call_info (NewFunctionInformation): Information about the new function call.

        Returns:
            tuple: A tuple containing the updated original node and the new function body.
        """
        func_call = self.create_call_statement_to_new_function(call_info)

        preamble = []
        postamble = []
        new_func_body = []
        for node in original_node.body:
            position = self.position_for_node(node)
            if position.start.line < self.config.start_line:
                preamble.append(node)
            elif position.start.line > self.config.end_line:
                postamble.append(node)
            else:
                new_func_body.append(node)

        if new_func_body and new_func_body[0].leading_lines:
            func_call = func_call.with_changes(
                leading_lines=new_func_body[0].leading_lines
            )
            new_func_body[0] = new_func_body[0].with_changes(leading_lines=[])

        updated_body = [*preamble, func_call, *postamble]

        return original_node.with_changes(body=updated_body), new_func_body

    def create_function_call(self, call_info: NewFunctionInformation, call_args):
        """
        Creates a function call node based on the given call information and arguments.

        This method constructs either a method call (if there's a receiver) or a
        regular function call. It also wraps the call in an Await node if the
        extracted code contains await statements, or in a Yield node with From if it
        contains yield statements.

        Args:
            call_info (NewFunctionInformation): Information about the function call.
            call_args: The arguments for the function call.

        Returns:
            cst.Call, cst.Await, or cst.Yield: The constructed function call node.
        """
        if call_info.receiver_name:
            func_call = cst.Call(
                cst.Attribute(
                    value=cst.Name(call_info.receiver_name),
                    attr=cst.Name(self.config.new_func_name),
                ),
                call_args,
            )
        else:
            func_call = cst.Call(cst.Name(self.config.new_func_name), call_args)

        if self.state.contains_await:
            func_call = cst.Await(func_call)
        elif self.state.contains_yield:
            func_call = cst.Yield(
                cst.From(func_call), lpar=[cst.LeftParen()], rpar=[cst.RightParen()]
            )
        return func_call

    def create_return_assignment_targets(
        self, call_info: NewFunctionInformation, func_call
    ) -> cst.SimpleStatementLine:
        """
        Creates assignment targets for the return variables of the extracted function.

        This function generates the appropriate CST nodes to assign the result of the
        extracted function call to either a single variable or a tuple of variables,
        depending on how many variables are being returned.

        Args:
            call_info (NewFunctionInformation): Information about the function call,
                including the variables to be returned.
            func_call: The CST node representing the extracted function call.

        Returns:
            cst.SimpleStatementLine: A CST node representing the assignment of the
                function call result to the appropriate variable(s).
        """
        if len(call_info.return_vars) == 1:
            assign_target = cst.AssignTarget(cst.Name(call_info.return_vars[0]))
        else:
            assign_target = cst.AssignTarget(
                cst.Tuple(
                    [cst.Element(cst.Name(var)) for var in call_info.return_vars],
                    lpar=[],
                    rpar=[],
                )
            )
        return cst.SimpleStatementLine(body=[cst.Assign([assign_target], func_call)])

    def create_call_statement_to_new_function(
        self, call_info: NewFunctionInformation
    ) -> cst.SimpleStatementLine:
        """
        Creates the call statement that will replace the original code.

        This method generates a CSTNode representing the call to the newly extracted function.
        It handles four cases:
        1. If the extracted code contains a yield statement, it wraps the function call in a yield from statement.
        2. If the extracted code contains a return statement, it wraps the function call in a return statement.
        3. If the extracted code assigns values to variables used later, it creates an assignment statement.
        4. Otherwise, it creates a simple expression statement with the function call.

        Args:
            call_info (NewFunctionInformation): Information about the new function call.

        Returns:
            cst.SimpleStatementLine: A CST node representing the call to the new function.
        """
        call_args = [cst.Arg(cst.Name(param)) for param in call_info.callsite_params]

        func_call = self.create_function_call(call_info, call_args)

        if self.state.contains_return:
            return cst.SimpleStatementLine(body=[cst.Return(func_call)])
        else:
            func_call = func_call.with_changes(lpar=[], rpar=[])
            if call_info.return_vars:
                return self.create_return_assignment_targets(call_info, func_call)
            else:
                return cst.SimpleStatementLine(body=[cst.Expr(func_call)])


class ExtractMethod(BaseCstLspCodeAction):
    name = "Extract Method"
    kind = lsp_types.CodeActionKind.RefactorExtract

    def refactor(
        self, module: cst.Module, start: lsp_types.Position, end: lsp_types.Position
    ) -> str | None:
        wrapper = cst.MetadataWrapper(module)
        transformer = FunctionExtractor(
            ExtractMethodConfig("new_func", start.line + 1, end.line + 1)
        )
        result = wrapper.visit(transformer)
        if transformer.state.added_new_function:
            return result.code
        return None
