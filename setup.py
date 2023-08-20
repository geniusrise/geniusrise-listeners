from setuptools import find_packages, setup

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="genius_streaming_spouts",
    version="0.1.0",
    packages=find_packages(exclude=["tests", "tests.*"]),
    install_requires=[],
    python_requires=">=3.10",
    author="ixaxaar",
    author_email="ixaxaar@geniusrise.ai",
    description="Streaming spouts for geniusrise",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ixaxaar/streaming-spouts",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
