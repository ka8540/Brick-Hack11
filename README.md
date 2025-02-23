# Lumi: Your Personal AI-Powered Productivity Assistant

<div align="center">
  <img src="https://github.com/user-attachments/assets/8b322d79-0c53-4ade-a98f-ac3da264d867" alt="logo" width="200"/>
</div>


## Overview

Lumi is a cutting-edge, open-source productivity assistant designed to streamline your daily tasks and boost your efficiency. Leveraging uses Realtime API for fast speech-to-speech experiences, It understands your natural language commands and seamlessly integrates with various tools and services to help you manage your schedule, find information, automate repetitive tasks, and much more.



## Features
<img width="1439" alt="lumihomepage" src="https://github.com/user-attachments/assets/3aad1116-0b0a-470b-a771-b262a7d20aca" />

This project offers a range of features powered by various tools and integrations:

- **Real-time Stock Data**: Fetch and visualize stock prices using the `query_stock_price` and `draw_plotly_chart` tools.
- **AI-Powered Image Generation**: Create images from text prompts using the `generate_image` tool, leveraging DALL-E.
- **Internet Search**: Access real-time information from the web using the `internet_search` tool with Tavily API.
- **Content Creation**:
    - Draft engaging LinkedIn posts with the `draft_linkedin_post` tool.
    - Generate personalized emails using the `draft_email` tool.
    - Create Python files from descriptions using the `create_python_file` tool.
- **YouTube Video Summarization**: Automatically generate structured notes from YouTube videos using the `generate_youtube_notes` tool.
- **Web Browsing**: Open URLs directly in the user's default browser with the `open_browser` tool.
- **Voice Interaction**: Interact with the system using voice commands, powered by Speechmatics Flow for real-time transcription.
- **Customizable Chat Interface**: Engage with the system through an interactive chat interface built with Chainlit.

## Getting Started

### Prerequisites

Before running this project, ensure you have the following:

- **Python 3.8+**: This project requires Python 3.8 or higher.
- **API Keys**: Obtain and set the following API keys as environment variables.
```OPENAI_API_KEY=your_openai_api_key
TAVILY_API_KEY=your_tavily_api_key
SPEECHMATICS_AUTH_TOKEN=your_speechmatics_auth_token
OPENAI_API_KEY=your_openai_api_key
GROQ_API_KEY = your_groq_api_key
```


### Installation

1.  **Clone the Repository:**

    ```
    git clone https://github.com/ka8540/Brick-Hack11.git
    cd Brick-Hack11
    ```

2.  **Create a Virtual Environment (Recommended):**

    ```
    python -m venv venv
    source venv/bin/activate  # On Linux/macOS
    venv\Scripts\activate   # On Windows
    ```

3.  **Install Dependencies:**

    ```
    pip install -r requirements.txt
    ```

4.  **Configuration:**

    *   Create a `.env` file in the root directory of the project.  This file will store your API keys and other sensitive information.
    *   Populate the `.env` file with the necessary environment variables (see the "Environment Variables" section below).

### Tools

This project provides a set of tools that can be used to perform various tasks. Here's a brief overview of each tool:

- **query_stock_price**: Queries stock price information for a given symbol and time period.

- **draw_plotly_chart**: Draws stock chart. Auto-fetches data if needed. Provide either chart_data OR symbol+period.

<img width="1440" alt="ChartTool" src="https://github.com/user-attachments/assets/cd26e6d2-7b8d-4beb-92ee-8d6f92a860ea" />
<img width="1439" alt="ChartToolInteractive" src="https://github.com/user-attachments/assets/4652783a-70bf-4a94-9793-4bee6b29a995" />

- **generate_image**: Generates an image based on a given prompt using DALL-E.
  
<img width="1439" alt="imagetool" src="https://github.com/user-attachments/assets/4e70973a-b123-4233-9474-377e7dce1e0c" />

- **internet_search**: Search the internet for real-time information using Tavily's search API.

<img width="1440" alt="SearchTool" src="https://github.com/user-attachments/assets/25d8e8c0-8bcb-42d1-af96-cac5d879b2fc" />
<img width="1440" alt="SearchTool2" src="https://github.com/user-attachments/assets/a33a5764-f4f0-4e2d-b256-0c2dbd01e6bc" />

- **draft_linkedin_post**: Creates a LinkedIn post draft and provides it for copying.

 <img width="1440" alt="linkedin" src="https://github.com/user-attachments/assets/9ddf8c16-140e-434c-8da4-0d999468a16b" />

- **create_python_file**: Creates a Python file based on a given topic or content description.
  
- **execute_python_file**: Executes a Python file in the scratchpad directory.

  <img width="1440" alt="pythonoutput" src="https://github.com/user-attachments/assets/5d58dedc-db98-4b59-bb83-330e59ab2ffe" />

- **open_browser**: Opens a URL in the user's default web browser.
<img width="1438" alt="BrowserTool" src="https://github.com/user-attachments/assets/21582aaa-3d5c-426f-9da2-5445921f4d50" />

- **draft_email**: Drafts a personalized email based on recipient and context.

  <img width="1440" alt="EmailTool" src="https://github.com/user-attachments/assets/e35b2a91-9dcd-4d13-ad0e-6ac01d5df04d" />

- **generate_youtube_notes**: Generates structured notes from YouTube videos. Auto-triggers when user mentions: notes, summary, key points, or video analysis. Always uses stored YouTube URL.

<img width="1437" alt="ytnotes2" src="https://github.com/user-attachments/assets/bbae64e5-ee7a-43d8-ae8f-67cbe6256f42" />

<img width="1440" alt="ytnotes1" src="https://github.com/user-attachments/assets/a27fa966-62a4-4742-a302-c93607268b20" />
