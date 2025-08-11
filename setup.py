from setuptools import find_packages, setup

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="theframe",
    version="1.0.0",
    author="David Rubert",
    author_email="david.rubert@gmail.com",
    description="Upload a random image from a curated collection of paintings to your Samsung TheFrameTV",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/theframe",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "samsungtvws[async,encrypted]>=2.0.0",
        "pillow>=10.0.0",
        "python-dotenv>=1.0.0",
        "ollama>=0.1.7",
        "python-slugify>=8.0.0",
        "httpx>=0.25.0",
        "aiohttp>=3.8.0",
        "pydantic>=2.0.0",
        "rich>=13.0.0",
        "typing-extensions>=4.8.0",
    ],
    entry_points={
        "console_scripts": [
            "theframe=main:main",
        ],
    },
)
