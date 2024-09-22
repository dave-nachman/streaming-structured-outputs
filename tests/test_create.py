from typing import List

import pytest
from pydantic import BaseModel

from streaming_structured_outputs.create import create

pytest_plugins = ["pytest_asyncio"]


@pytest.mark.asyncio
async def test_create():
    class Recipe(BaseModel):
        description: str
        ingredients: List[str]
        instructions: List[str]

    count = 0
    async for result in create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": "I'd like a recipe for chicken parm",
            },
        ],
        response_format=Recipe,
    ):
        count += 1
        assert isinstance(result, Recipe)
    assert count > 0
