# Streaming Structured Outputs

This library allows you to stream responses that follow the [Structured Outputs](https://platform.openai.com/docs/guides/structured-outputs/introduction) from OpenAI LLMs, providing an async iterator of (potentially partial) instances of your [Pydantic](https://docs.pydantic.dev/latest/) model.

This was written as a proof-of-concept/learning experience for my personal use; for a production-ready implementation of the same idea, see the streaming partial responses feature of [Instructor](https://python.useinstructor.com/concepts/partial/).

## Motivation

While using structured outputs is a powerful tool for controlling LLM output and integrating with a broader system, a downside is that you lose the advantage of being able to use partial output in a streaming manner. This library aims to address this by providing a way to stream structured outputs from a LLM, providing an async iterator of (potentially partial) instances of your Pydantic model.

## Example

https://github.com/user-attachments/assets/1daf7074-5922-431e-b7ef-8b3b8ee79563

```python
from streaming_structured_outputs import create

class Recipe(BaseModel):
    description: str
    ingredients: List[str]
    instructions: List[str]


async for recipe in create(
    model="gpt-4o-mini",
    messages=[
        {"role": "user", "content": "Please write a chicken parm recipe."},
    ],
    response_format=Recipe,
):
    print(recipe)
```
