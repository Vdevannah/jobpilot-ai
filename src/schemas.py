from pydantic import BaseModel, ConfigDict


class JobResponse(BaseModel):
    id: int
    title: str
    company: str
    location: str
    url: str
    source: str

    model_config = ConfigDict(from_attributes=True)
