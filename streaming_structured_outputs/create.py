import json
import os
from typing import AsyncGenerator, Dict, List, Optional, Type

import httpx
from httpx_sse import aconnect_sse
from pydantic import BaseModel
from pydantic_core import from_json
from pydantic_partial import create_partial_model


def parse_output(output: str, model: Type[BaseModel]) -> Optional[BaseModel]:
    try:
        json_content = from_json(output, allow_partial=True)
        return create_partial_model(model).model_validate(json_content, strict=False)
    except Exception:
        # if parsing fails, just return None
        return None


async def create(
    model: str,
    messages: List[Dict[str, str]],
    response_format: BaseModel,
    url: str = "https://api.openai.com/v1/chat/completions",
    api_key: Optional[str] = None,
    httpx_client: Optional[httpx.AsyncClient] = None,
    **kwargs,
) -> AsyncGenerator[BaseModel, None]:
    """
    Create an async generator that streams structured outputs from a language model.

    This function sends a request to a language model API and yields parsed responses
    as they are received, allowing for streaming of structured data.

    The function parameters mirror the [openai.chat.completions.create](https://platform.openai.com/docs/api-reference/chat/create) function.

    Args:
        model (str): The name of the language model to use.
        messages (List[Dict[str, str]]): A list of message dictionaries to send to the model.
        response_format (BaseModel): A Pydantic model defining the structure of the expected response.
        url (str, optional): The API endpoint URL. Defaults to OpenAI's chat completions endpoint.
        api_key (str, optional): The API key for authentication. Defaults to the OPENAI_API_KEY environment variable.
        httpx_client (httpx.AsyncClient, optional): An async HTTP client. Defaults to a new httpx.AsyncClient instance.
        **kwargs: Additional keyword arguments to pass to the API request.

    Yields:
        BaseModel: Instances of the response_format model, potentially partially filled.

    Raises:
        ValueError: If the OPENAI_API_KEY environment variable is not set and no api_key is provided.

    Example:
        >>> class Recipe(BaseModel):
        ...     name: str
        ...     ingredients: List[str]
        ...     instructions: List[str]
        ...
        >>> async for recipe in create(
        ...     model="gpt-4o-mini",
        ...     messages=[{"role": "user", "content": "Create a recipe for chocolate cake"}],
        ...     response_format=Recipe
        ... ):
        ...     print(recipe)
    """

    if not api_key:
        api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set.")

    if httpx_client is None:
        httpx_client = httpx.AsyncClient()

    body = {
        "model": model,
        "messages": messages,
        "stream": True,
        # response_format isn't supported by the streaming API, so we need to use tools instead
        "tool_choice": "required",
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": response_format.__name__,
                    "description": "Parse the output as a Pydantic model",
                    "parameters": response_format.model_json_schema(),
                },
            }
        ],
        **kwargs,
    }

    async with httpx_client:
        async with aconnect_sse(
            httpx_client,
            "POST",
            url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=body,
        ) as event_source:
            output = ""
            seen = set()

            async for event in event_source.aiter_sse():
                # [DONE] is a special event that indicates the end of the stream
                if event.data == "[DONE]":
                    continue

                data = json.loads(event.data)

                try:
                    output += data["choices"][0]["delta"]["tool_calls"][0]["function"][
                        "arguments"
                    ]
                except KeyError:
                    pass

                # try parsing the output as our response format
                parsed = parse_output(output, response_format)

                # if we successfully parsed and haven't yielded this instance yet, yield it
                if parsed and str(parsed) not in seen:
                    seen.add(str(parsed))
                    yield parsed
