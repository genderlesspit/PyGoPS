 from setuptools import setup, find_packages

setup(
    name="pygops",
    version="0.1.0",
    description="Python wrapper for Go applications with PowerShell launcher",
    author="PyGoPS Team",
    packages=find_packages(),
    include_package_data=True,
    package_data={"pygops": ["scripts/*.ps1"]},
    install_requires=["loguru", "toomanyports", "aiohttp"],
    python_requires=">=3.8",
)
