from dataclasses import dataclass


@dataclass(slots=True)
class Customer:
    name: str
    contact_person: str = ""
    phone: str = ""
    email: str = ""
    address: str = ""
    shipping_address: str = ""
    gstin: str = ""
    id: int | None = None

    def validate(self) -> None:
        if not self.name.strip():
            raise ValueError("Customer name is required")
