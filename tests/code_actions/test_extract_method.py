import textwrap

import libcst as cst
from libcst.metadata import CodeRange
from cst_lsp.code_actions.extract_method import (
    ExtractMethodConfig,
    FunctionExtractor,
)


def source_to_refactor_input(source_code: str):
    lines = []
    start_line = 0
    end_line = 0
    for i, line in enumerate(source_code.splitlines()):
        if "# start" == line.strip():
            start_line = i + 1
        elif "# end" == line.strip():
            end_line = i - 1
        else:
            lines.append(line)
    source_code = "\n".join(lines)
    return source_code, start_line, end_line


def refactor_with_comments(source_code: str, new_func_name: str) -> str:
    source_code, start_line, end_line = source_to_refactor_input(source_code)

    tree = cst.parse_module(source_code)
    wrapper = cst.MetadataWrapper(tree)
    config = ExtractMethodConfig(
        new_func_name, CodeRange((start_line, 0), (end_line, 0))
    )
    transformer = FunctionExtractor(config)
    modified_tree = wrapper.visit(transformer)
    return modified_tree.code


def test_extract_method_simple():
    source_code = textwrap.dedent(
        """
        def original_function():
            x: int = 5
            y: float = 10.0
            # start
            z = x + y
            print(f"Sum is: {z}")
            # end
            a = z * 2
            return a

        # Other code...
    """
    )

    expected_output = textwrap.dedent(
        """
        def extracted_function(x: int, y: float):
            z = x + y
            print(f"Sum is: {z}")
            return z

        def original_function():
            x: int = 5
            y: float = 10.0
            z = extracted_function(x, y)
            a = z * 2
            return a

        # Other code...
    """
    )

    refactored_code = refactor_with_comments(source_code, "extracted_function")
    assert refactored_code.strip() == expected_output.strip()


def test_extract_method_with_control_flow():
    source_code = textwrap.dedent(
        """
        def complex_function(a: int, b: int) -> int:
            result = 0
            for i in range(a):
                # start
                if i % 2 == 0:
                    result += i * b
                else:
                    result += -i * b
                # end
            print(f"Final result: {result}")
            return result

        # Other code...
    """
    )

    expected_output = textwrap.dedent(
        """
        def extracted_function(b: int, result: int, i) -> int:
            if i % 2 == 0:
                result += i * b
            else:
                result += -i * b
            return result

        def complex_function(a: int, b: int) -> int:
            result = 0
            for i in range(a):
                result = extracted_function(b, result, i)
            print(f"Final result: {result}")
            return result

        # Other code...
    """
    )

    refactored_code = refactor_with_comments(source_code, "extracted_function")
    assert refactored_code.strip() == expected_output.strip()


def test_extract_method_with_multiple_returns():
    source_code = textwrap.dedent(
        """
        def calculate_discount(price: float, is_member: bool) -> float:
            # start
            if is_member:
                if price > 100:
                    return price * 0.8
                else:
                    return price * 0.9
            else:
                if price > 200:
                    return price * 0.95
                else:
                    return price
            # end

        # Other code...
    """
    )

    expected_output = textwrap.dedent(
        """
        def extracted_function(price: float, is_member: bool) -> float:
            if is_member:
                if price > 100:
                    return price * 0.8
                else:
                    return price * 0.9
            else:
                if price > 200:
                    return price * 0.95
                else:
                    return price

        def calculate_discount(price: float, is_member: bool) -> float:
            return extracted_function(price, is_member)

        # Other code...
    """
    )

    refactored_code = refactor_with_comments(source_code, "extracted_function")
    assert refactored_code.strip() == expected_output.strip()


def test_extract_method_from_class():
    source_code = textwrap.dedent(
        """
        class MyClass:
            def __init__(self, value: int):
                self.value = value

            def process(self, multiplier: int) -> int:
                # start
                result: int = self.value * multiplier
                if result > 100:
                    result = 100
                # end
                return result

        # Other code...
    """
    )

    expected_output = textwrap.dedent(
        """
        class MyClass:
            def __init__(self, value: int):
                self.value = value

            def extracted_function(self, multiplier: int) -> int:
                result: int = self.value * multiplier
                if result > 100:
                    result = 100
                return result

            def process(self, multiplier: int) -> int:
                result = self.extracted_function(multiplier)
                return result

        # Other code...
    """
    )

    refactored_code = refactor_with_comments(source_code, "extracted_function")
    assert refactored_code.strip() == expected_output.strip()


def test_extract_method_from_instance_method():
    source_code = textwrap.dedent(
        """
        class MyClass:
            def __init__(self, value: int):
                self.value = value

            def process(self, multiplier: int) -> int:
                # start
                result: int = self.value * multiplier
                if result > 100:
                    result = 100
                # end
                return result

        # Other code...
    """
    )

    expected_output = textwrap.dedent(
        """
        class MyClass:
            def __init__(self, value: int):
                self.value = value

            def extracted_function(self, multiplier: int) -> int:
                result: int = self.value * multiplier
                if result > 100:
                    result = 100
                return result

            def process(self, multiplier: int) -> int:
                result = self.extracted_function(multiplier)
                return result

        # Other code...
    """
    )

    refactored_code = refactor_with_comments(source_code, "extracted_function")
    assert refactored_code.strip() == expected_output.strip()


def test_extract_method_from_class_method():
    source_code = textwrap.dedent(
        """
        class MyClass:
            value = 10

            @classmethod
            def process(cls, multiplier: int) -> int:
                # start
                result: int = cls.value * multiplier
                if result > 100:
                    result = 100
                # end
                return result

        # Other code...
    """
    )

    expected_output = textwrap.dedent(
        """
        class MyClass:
            value = 10

            @classmethod
            def extracted_function(cls, multiplier: int) -> int:
                result: int = cls.value * multiplier
                if result > 100:
                    result = 100
                return result

            @classmethod
            def process(cls, multiplier: int) -> int:
                result = cls.extracted_function(multiplier)
                return result

        # Other code...
    """
    )

    refactored_code = refactor_with_comments(source_code, "extracted_function")
    assert refactored_code.strip() == expected_output.strip()


def test_extract_method_from_static_method():
    source_code = textwrap.dedent(
        """
        class MyClass:
            @staticmethod
            def process(value: int, multiplier: int) -> int:
                # start
                result: int = value * multiplier
                if result > 100:
                    result = 100
                # end
                return result

        # Other code...
    """
    )

    expected_output = textwrap.dedent(
        """
        class MyClass:
            @staticmethod
            def extracted_function(value: int, multiplier: int) -> int:
                result: int = value * multiplier
                if result > 100:
                    result = 100
                return result

            @staticmethod
            def process(value: int, multiplier: int) -> int:
                result = MyClass.extracted_function(value, multiplier)
                return result

        # Other code...
    """
    )

    refactored_code = refactor_with_comments(source_code, "extracted_function")
    assert refactored_code.strip() == expected_output.strip()


def test_extract_method_multiple_returns_typed():
    source_code = textwrap.dedent(
        """
        def process_data(data: list[int]) -> tuple[int, float]:
            total: int = 0
            average: float = 0.0
            # start
            for item in data:
                total += item
            if len(data) > 0:
                average = total / len(data)
            # end
            return total, average

        # Other code...
    """
    )

    expected_output = textwrap.dedent(
        """
        def extracted_function(data: list[int], total: int) -> tuple[int, float]:
            for item in data:
                total += item
            if len(data) > 0:
                average = total / len(data)
            return total, average

        def process_data(data: list[int]) -> tuple[int, float]:
            total: int = 0
            average: float = 0.0
            total, average = extracted_function(data, total)
            return total, average

        # Other code...
    """
    )

    refactored_code = refactor_with_comments(source_code, "extracted_function")
    assert refactored_code.strip() == expected_output.strip()


def test_extract_method_multiple_returns_untyped():
    source_code = textwrap.dedent(
        """
        def analyze_text(text):
            word_count = 0
            char_count = 0
            # start
            words = text.split()
            word_count += len(words)
            char_count = len(text)
            # end
            return word_count, char_count

        # Other code...
    """
    )

    expected_output = textwrap.dedent(
        """
        def extracted_function(text, word_count):
            words = text.split()
            word_count += len(words)
            char_count = len(text)
            return word_count, char_count

        def analyze_text(text):
            word_count = 0
            char_count = 0
            word_count, char_count = extracted_function(text, word_count)
            return word_count, char_count

        # Other code...
    """
    )

    refactored_code = refactor_with_comments(source_code, "extracted_function")
    assert refactored_code.strip() == expected_output.strip()


def test_extract_method_from_nested_method():
    source_code = textwrap.dedent(
        """
        class OuterClass:
            def outer_method(self):
                def inner_method():
                    x = 10
                    y = 20
                    # start
                    result = x + y
                    print(f"Sum is: {result}")
                    # end
                    return result
                return inner_method()

        # Other code...
    """
    )

    expected_output = textwrap.dedent(
        """
        class OuterClass:
            def outer_method(self):
                def extracted_function(x, y):
                    result = x + y
                    print(f"Sum is: {result}")
                    return result

                def inner_method():
                    x = 10
                    y = 20
                    result = extracted_function(x, y)
                    return result
                return inner_method()

        # Other code...
    """
    )

    refactored_code = refactor_with_comments(source_code, "extracted_function")
    assert refactored_code.strip() == expected_output.strip()


def test_extract_method_leading_lines():
    source_code = textwrap.dedent(
        """
        def original_function():
            x = 5
            y = 10

            # start
            # This is a comment
            z = x + y
            print(f"Sum is: {z}")
            # end
            return z

        # Other code...
    """
    )

    expected_output = textwrap.dedent(
        """
        def extracted_function(x, y):
            z = x + y
            print(f"Sum is: {z}")
            return z

        def original_function():
            x = 5
            y = 10

            # This is a comment
            z = extracted_function(x, y)
            return z

        # Other code...
    """
    )

    refactored_code = refactor_with_comments(source_code, "extracted_function")
    assert refactored_code.strip() == expected_output.strip()


def test_extract_method_tuple_assignment():
    source_code = textwrap.dedent(
        """
        def process_data(data: list[int]) -> tuple[int, float]:
            total, count = 0, 0
            # start
            for item in data:
                total += item
                count += 1
            average = total / count if count > 0 else 0.0
            # end
            return total, average

        # Other code...
    """
    )

    expected_output = textwrap.dedent(
        """
        def extracted_function(data: list[int], total, count):
            for item in data:
                total += item
                count += 1
            average = total / count if count > 0 else 0.0
            return total, average

        def process_data(data: list[int]) -> tuple[int, float]:
            total, count = 0, 0
            total, average = extracted_function(data, total, count)
            return total, average

        # Other code...
    """
    )

    refactored_code = refactor_with_comments(source_code, "extracted_function")
    assert refactored_code.strip() == expected_output.strip()


def test_extract_method_with_statement():
    source_code = textwrap.dedent(
        """
        def process_file(filename: str) -> str:
            content = ""
            with open(filename, 'r') as file:
            # start
                content = file.read()
                content = content.upper()
            # end
            return content

        # Other code...
    """
    )

    expected_output = textwrap.dedent(
        """
        def extracted_function(content: str, file) -> str:
            content = file.read()
            content = content.upper()
            return content

        def process_file(filename: str) -> str:
            content = ""
            with open(filename, 'r') as file:
                content = extracted_function(content, file)
            return content

        # Other code...
    """
    )

    refactored_code = refactor_with_comments(source_code, "extracted_function")
    assert refactored_code.strip() == expected_output.strip()


def test_extract_method_array_index_assignment():
    source_code = textwrap.dedent(
        """
        def process_array(arr: list[int]) -> list[int]:
            index = 0
            start = 0
            # start
            while index < len(arr):
                arr[index] = arr[index] * 2
                arr[start] = index
                index += 1
            # end
            return arr

        # Other code...
    """
    )

    expected_output = textwrap.dedent(
        """
        def extracted_function(arr: list[int], index, start):
            while index < len(arr):
                arr[index] = arr[index] * 2
                arr[start] = index
                index += 1

        def process_array(arr: list[int]) -> list[int]:
            index = 0
            start = 0
            extracted_function(arr, index, start)
            return arr

        # Other code...
    """
    )

    refactored_code = refactor_with_comments(source_code, "extracted_function")
    assert refactored_code.strip() == expected_output.strip()


def test_extract_method_with_walrus_operator():
    source_code = textwrap.dedent(
        """
        def process_numbers(numbers: list[int]) -> list[int]:
            result = []
            while (n := len(numbers)) > 0:
                # start
                if (last := numbers.pop() + n) % 2 == 0:
                    result.append(last * 2)
                else:
                    result.append(last * 3)
                # end
            return result

        # Other code...
    """
    )

    expected_output = textwrap.dedent(
        """
        def extracted_function(numbers: list[int], result: list[int], n):
            if (last := numbers.pop() + n) % 2 == 0:
                result.append(last * 2)
            else:
                result.append(last * 3)

        def process_numbers(numbers: list[int]) -> list[int]:
            result = []
            while (n := len(numbers)) > 0:
                extracted_function(numbers, result, n)
            return result

        # Other code...
    """
    )

    refactored_code = refactor_with_comments(source_code, "extracted_function")
    assert refactored_code.strip() == expected_output.strip()


def test_extract_method_array_access():
    source_code = textwrap.dedent(
        """
        def process_data(data):
            result = []
            value = 0
            # start
            for item in data:
                if item.value > 10:
                    result.append(item.name)
            # end
            return result

        # Other code...
    """
    )

    expected_output = textwrap.dedent(
        """
        def extracted_function(data, result):
            for item in data:
                if item.value > 10:
                    result.append(item.name)

        def process_data(data):
            result = []
            value = 0
            extracted_function(data, result)
            return result

        # Other code...
    """
    )

    refactored_code = refactor_with_comments(source_code, "extracted_function")
    assert refactored_code.strip() == expected_output.strip()


def test_extract_method_empty_body():
    source_code = textwrap.dedent(
        """
        def original_function(x: int, y: int) -> int:
            a = some_func(
            # start
                another_func(y),
            # end
                third_func(a, b)
            )
            return a

        # Other code...
    """
    )

    expected_output, _, _ = source_to_refactor_input(source_code)

    refactored_code = refactor_with_comments(source_code, "extracted_function")
    assert refactored_code.strip() == expected_output.strip()


def test_extract_method_with_async_await():
    source_code = textwrap.dedent(
        """
        async def process_data(data: list[int]) -> list[int]:
            result = []
            # start
            for item in data:
                processed = await async_process(item)
                result.append(processed)
            # end
            return result

        # Other code...
    """
    )

    expected_output = textwrap.dedent(
        """
        async def extracted_function(data: list[int], result: list[int]):
            for item in data:
                processed = await async_process(item)
                result.append(processed)

        async def process_data(data: list[int]) -> list[int]:
            result = []
            await extracted_function(data, result)
            return result

        # Other code...
    """
    )

    refactored_code = refactor_with_comments(source_code, "extracted_function")
    assert refactored_code.strip() == expected_output.strip()


def test_extract_method_without_async_await():
    source_code = textwrap.dedent(
        """
        async def process_data(data: list[int]) -> list[int]:
            result = []
            # start
            for item in data:
                processed = sync_process(item)
                result.append(processed)
            # end
            await some_other_async_function()
            return result

        # Other code...
    """
    )

    expected_output = textwrap.dedent(
        """
        def extracted_function(data: list[int], result: list[int]):
            for item in data:
                processed = sync_process(item)
                result.append(processed)

        async def process_data(data: list[int]) -> list[int]:
            result = []
            extracted_function(data, result)
            await some_other_async_function()
            return result

        # Other code...
    """
    )

    refactored_code = refactor_with_comments(source_code, "extracted_function")
    assert refactored_code.strip() == expected_output.strip()


def test_extract_method_with_yield():
    source_code = textwrap.dedent(
        """
        def original_function():
            x = 5
            y = 10
            # start
            yield x
            yield y
            # end
            z = x + y
            yield z

        # Other code...
    """
    )

    expected_output = textwrap.dedent(
        """
        def extracted_function(x, y):
            yield x
            yield y

        def original_function():
            x = 5
            y = 10
            yield from extracted_function(x, y)
            z = x + y
            yield z

        # Other code...
    """
    )

    refactored_code = refactor_with_comments(source_code, "extracted_function")
    assert refactored_code.strip() == expected_output.strip()


def test_extract_method_with_yield_and_return():
    source_code = textwrap.dedent(
        """
        def original_function():
            # start
            yield 1
            x = 3
            yield 2
            y = 4
            # end
            return x + y

        # Other code...
    """
    )

    expected_output = textwrap.dedent(
        """
        def extracted_function():
            yield 1
            x = 3
            yield 2
            y = 4
            return x, y

        def original_function():
            x, y = yield from extracted_function()
            return x + y

        # Other code...
    """
    )

    refactored_code = refactor_with_comments(source_code, "extracted_function")
    assert refactored_code.strip() == expected_output.strip()


def test_extract_method_with_yield_and_explicit_return():
    source_code = textwrap.dedent(
        """
        def original_function():
            # start
            yield 1
            yield 2
            return 3
            # end

        # Other code...
    """
    )

    expected_output = textwrap.dedent(
        """
        def extracted_function():
            yield 1
            yield 2
            return 3

        def original_function():
            return (yield from extracted_function())

        # Other code...
    """
    )

    refactored_code = refactor_with_comments(source_code, "extracted_function")
    assert refactored_code.strip() == expected_output.strip()
