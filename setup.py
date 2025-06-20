from setuptools import find_packages, setup

setup(
    name="pinball_map_bot",
    version="0.1.0",
    description="A Discord bot to monitor pinballmap.com for machine changes.",
    author="Froeht",  # Replace with your name
    author_email="froeht@users.noreply.github.com",  # Replace with your email
    packages=find_packages(),
    install_requires=[
        "discord.py",
        "requests",
        "python-dotenv",
        "sqlalchemy>=2.0.0",
        "pytest",
    ],
    entry_points={
        "console_scripts": [
            "pinball-bot=src.main:main",
        ],
    },
    python_requires=">=3.9",  # Specify your Python version
)
