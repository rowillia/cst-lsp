from collections import defaultdict
from dataclasses import dataclass, field

import libcst as cst
import libcst.matchers as m
from libcst.metadata import (
    CodePosition,
    CodeRange,
    PositionProvider,
)


@dataclass
class VariableCollectorState:
    function_stack: list[cst.FunctionDef] = field(default_factory=list)
    count_name_as_assign: bool = False
    subscript_depth: int = 0
    attribute_depth: int = 0
    usage_tracked_for_attribute: bool = False


class VariableCollector(m.MatcherDecoratableVisitor):
    METADATA_DEPENDENCIES = (PositionProvider,)

    def __init__(self):
        super().__init__()
        self.assignments: dict[str, set[CodePosition]] = defaultdict(set)
        self.usages: dict[str, set[CodePosition]] = defaultdict(set)
        self.types: dict[str, cst.Annotation] = {}
        self._state = VariableCollectorState()

    def position_for_node(self, node: cst.CSTNode) -> CodeRange:
        position = self.get_metadata(PositionProvider, node)
        assert isinstance(position, CodeRange)
        return position

    def _track_node(
        self,
        node: cst.CSTNode,
        is_assignment: bool,
        annotation: cst.Annotation | None = None,
    ):
        if not isinstance(node, cst.Name):
            return
        position = self.position_for_node(node)
        if is_assignment:
            self.assignments[node.value].add(position.start)
            if annotation:
                self.types[node.value] = annotation
        else:
            self.usages[node.value].add(position.start)

    def visit_AnnAssign(self, node: cst.AnnAssign) -> None:
        self._track_node(node.target, True, node.annotation)

    @m.visit(m.AugAssign() | m.NamedExpr() | m.For())
    def visit_node_with_target(
        self, node: cst.AugAssign | cst.NamedExpr | cst.For
    ) -> None:
        self._track_node(node.target, True)

    def visit_Param(self, node: cst.Param) -> None:
        self._track_node(node.name, True, node.annotation)

    def visit_Name(self, node: cst.Name) -> None:
        if self._state.attribute_depth > 0:
            # If we're currently within an attribute we don't
            # want to track any names, e.g. `x.a.b.c` should
            # track `x`, but not `a`, `b`, or `c`.
            # In this case, the tracking of `x` is handled in
            # `leave_Attribute`.
            return
        is_assignment = (
            self._state.count_name_as_assign and self._state.subscript_depth == 0
        )
        self._track_node(node, is_assignment)

    def visit_With(self, node: cst.With) -> None:
        for item in node.items:
            if isinstance(item.asname, cst.AsName):
                self._track_node(item.asname.name, True)

    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:
        # Track functions so we can infer types from return statements.
        self._state.function_stack.append(node)

    def leave_FunctionDef(self, original_node: cst.FunctionDef) -> None:
        self._state.function_stack.pop()

    def visit_Return(self, node: cst.Return) -> None:
        # If we're within a function and encounter a return statement we can
        # infer that the type of the item being returned is the same type
        # as the function itself.  Currently this only works when returning
        # a name, but could be made to work with tuples.
        # e.g.
        #
        # def foo(x) -> int
        #     return x
        #
        # We can infer that the type of `x` is `int`
        if not self._state.function_stack or not isinstance(node.value, cst.Name):
            return
        current_function = self._state.function_stack[-1]
        if current_function.returns:
            stripped_return = current_function.returns.with_changes(
                whitespace_before_indicator=cst.SimpleWhitespace(""),
                whitespace_after_indicator=cst.SimpleWhitespace(" "),
            )
            self.types[node.value.value] = stripped_return

    def visit_AssignTarget(self, node: cst.AssignTarget) -> None:
        # This handles everything on the left-hand side of an equals sign,
        # including multiple assignments like a, b, c = 3, 4, 5
        self._state.count_name_as_assign = True

    def leave_AssignTarget(self, original_node: cst.AssignTarget) -> None:
        self._state.count_name_as_assign = False

    def visit_Subscript(self, node: cst.Subscript) -> None:
        # We don't' want to consider names within a subscript as being
        # assignments, so we have to track if we are within a subscript
        # or not.
        # e.g. x[a] = 12
        # `x` should be an assignment, `a` should be a usage
        self._state.subscript_depth += 1

    def leave_Subscript(self, original_node: cst.Subscript) -> None:
        self._state.subscript_depth -= 1

    def visit_Attribute(self, node: cst.Attribute) -> None:
        # With a chain of attribute accesses, we only want to treat
        # the first element in the chain as being a local symbol
        # (either as an assignment or as a usage).  To accomplish
        # this, we track the current attribute depth and upon leaving
        # an attribute check to see if we've already storaged the
        # usage for that variable.  It will always be a usage as, even
        # if we're on the LHS of an assignment, the attribute is being
        # mutated not the underlying instance.
        # e.g. `x.a = 3` doesn't mutate the instance of `x` and therefore
        # x is just a usage.
        self._state.attribute_depth += 1

    def leave_Attribute(self, original_node: cst.Attribute) -> None:
        self._state.attribute_depth -= 1
        if not self._state.usage_tracked_for_attribute:
            self._track_node(original_node.value, False)
            self._state.usage_tracked_for_attribute = True
        if self._state.attribute_depth == 0:
            self._state.usage_tracked_for_attribute = False
