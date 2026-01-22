from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database (PostgreSQL)
    database_url: str = "postgresql://postgres:postgres@localhost:5432/autosaas"
    
    # LLM Configuration (OpenAI-compatible endpoint)
    llm_api_key: str = ""
    llm_base_url: str = "https://api.groq.com/openai/v1"
    llm_model: str = "meta-llama/llama-4-maverick-17b-128e-instruct"
    
    # AgentQL
    agentql_api_key: str = ""
    
    # Browser Settings
    browser_headless: bool = False
    browser_user_data_dir: str = ""  # Path to Chrome profile (e.g., C:\Users\YourName\AppData\Local\Google\Chrome\User Data)
    max_concurrent_browsers: int = 3
    
    # Application
    max_retries: int = 3
    screenshot_dir: str = "./screenshots"
    log_level: str = "INFO"
    secret_key: str = "change-this-in-production"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
