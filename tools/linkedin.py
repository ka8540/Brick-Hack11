"""LinkedIn post drafting tool."""
import os
import chainlit as cl
from langchain.prompts import PromptTemplate
from pydantic import BaseModel, Field
from utils.ai_models import get_llm
from utils.common import logger, scratch_pad_dir


class LinkedInPost(BaseModel):
    """LinkedIn post draft."""

    content: str = Field(
        ...,
        description="The drafted LinkedIn post content",
    )


draft_linkedin_post_def = {
    "name": "draft_linkedin_post",
    "description": "Creates a LinkedIn post draft based on a given topic or content description.",
    "parameters": {
        "type": "object",
        "properties": {
            "topic": {
                "type": "string",
                "description": "The topic or content description for the LinkedIn post (e.g., 'The importance of AI ethics in modern technology').",
            },
        },
        "required": ["topic"],
    },
}


async def draft_linkedin_post_handler(topic):
    """Creates a LinkedIn post draft based on a given topic."""
    try:
        logger.info(f"📝 Drafting LinkedIn post on topic: '{topic}'")

        llm = get_llm("linkedin_post")

        structured_llm = llm.with_structured_output(LinkedInPost)

        system_template = """
        Create an engaging LinkedIn post for a given topic incorporating relevant emojis to capture attention and convey the message effectively. 

        # Topic
        {topic}

        # Steps
        1. **Identify the main message**: Determine the core topic or idea you want to communicate in the post.
        2. **Audience Consideration**: Tailor your language and tone to fit the audience you are addressing on LinkedIn.
        3. **Incorporate Emojis**: Select emojis that complement the text and reinforce the message without overwhelming it.
        4. **Structure the Post**: Organize the content to include an engaging opening, informative content, and a clear call-to-action if applicable.
        """

        prompt_template = PromptTemplate(
            input_variables=["topic"],
            template=system_template,
        )

        chain = prompt_template | structured_llm
        linkedin_post = chain.invoke({"topic": topic}).content

        filepath = os.path.join(scratch_pad_dir, "linkedin_post.md")
        with open(filepath, "w") as f:
            f.write(linkedin_post)

        logger.info(f"💾 LinkedIn post saved successfully at {filepath}")
        await cl.Message(content=f"LinkedIn post about '{topic}':\n\n{linkedin_post}").send()

        return linkedin_post

    except Exception as e:
        logger.error(f"❌ Error drafting LinkedIn post: {str(e)}")
        await cl.Message(content=f"An error occurred while drafting the LinkedIn post: {str(e)}").send()


draft_linkedin_post = (draft_linkedin_post_def, draft_linkedin_post_handler)
