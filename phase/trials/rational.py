from fractions import Fraction


RationalInput = Fraction | int | str


def parse_rational(value: RationalInput) -> Fraction:
    if isinstance(value, bool) or not isinstance(value, (Fraction, int, str)):
        raise ValueError('expected an exact rational input')
    try:
        return Fraction(value)
    except (ValueError, ZeroDivisionError) as error:
        raise ValueError('invalid rational value') from error


def encode_rational(value: RationalInput) -> str:
    return str(parse_rational(value))


def decode_rational(value: object) -> Fraction:
    if not isinstance(value, str):
        raise ValueError('rational encoding must be a string')
    number = parse_rational(value)
    if str(number) != value:
        raise ValueError('noncanonical rational encoding')
    return number
