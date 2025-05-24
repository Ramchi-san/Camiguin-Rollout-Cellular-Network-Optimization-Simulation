import re

def extract_numbers(input_string):
    """Extract all integers from a string using regex matching."""
    return [int(num) for num in re.findall(r'\b\d+\b', input_string)]

# Example usage
input_str = "10, 11, 12, 34 , 56, ..."
numbers_list = extract_numbers(input_str)
print(numbers_list)  # Output: [10, 11, 12, 34, 56]