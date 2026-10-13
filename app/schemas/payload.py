from pydantic import BaseModel, model_validator


class PayloadCreate(BaseModel):
    list_1: list[str]
    list_2: list[str]

    @model_validator(mode="after")
    def validate_equal_lengths(self):
        if len(self.list_1) != len(self.list_2):
            raise ValueError("Both lists must have the same length")
        return self


class PayloadCreated(BaseModel):
    id: str


class PayloadRead(BaseModel):
    output: str