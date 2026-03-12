import re


CPF_RE = re.compile(r"^\d{11}$")


def normalize_cpf(value: str) -> str:
    return "".join(ch for ch in value if ch.isdigit())


def is_valid_cpf(cpf: str) -> bool:
    digits = normalize_cpf(cpf)
    if not CPF_RE.match(digits):
        return False
    if digits == digits[0] * 11:
        return False

    def check_digit(base: str, factor: int) -> int:
        total = sum(int(num) * (factor - idx) for idx, num in enumerate(base))
        remainder = (total * 10) % 11
        return 0 if remainder == 10 else remainder

    first = check_digit(digits[:9], 10)
    second = check_digit(digits[:10], 11)
    return digits[-2:] == f"{first}{second}"


def mask_cpf(cpf: str) -> str:
    digits = normalize_cpf(cpf)
    if len(digits) != 11:
        return "***"
    return f"***.***.***-{digits[-2:]}"
