from pydantic import BaseModel, ConfigDict, Field, model_validator


class PreferenceInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    country: str = Field(min_length=1, max_length=80)
    partner_type: str = Field(min_length=1, max_length=40)


class PreferencesInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    preferences: list[PreferenceInput] = Field(max_length=50)

    @model_validator(mode="after")
    def distinct_pairs(self):
        pairs = [(p.country.casefold(), p.partner_type.casefold()) for p in self.preferences]
        if len(set(pairs)) != len(pairs):
            raise ValueError("Duplicate market preference")
        return self
