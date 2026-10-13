"""South Africa is the flagship country.

A public list that does not name a country puts a South African employer or
role ahead of every other country, then keeps the list's own date order.
Naming a country is a filter. Other countries stay in the result.
"""
from sqlalchemy import case, or_

from app.models.company import Company
from app.models.vacancy import Vacancy

FLAGSHIP_COUNTRY = "South Africa"


def flagship_role_rank():
    """0 when the employer or the stored role is in South Africa, else 1."""
    return case(
        (or_(Company.country == FLAGSHIP_COUNTRY, Vacancy.country == FLAGSHIP_COUNTRY), 0),
        else_=1,
    )


def flagship_employer_rank():
    """0 when the employer is in South Africa, else 1."""
    return case((Company.country == FLAGSHIP_COUNTRY, 0), else_=1)


def countries_flagship_first(names: list[str]) -> list[str]:
    """South Africa first, then the other names A to Z."""
    return sorted(names, key=lambda name: (0 if name == FLAGSHIP_COUNTRY else 1, name.lower()))
