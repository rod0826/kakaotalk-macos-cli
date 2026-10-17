from setuptools import setup, find_namespace_packages

setup(
    name="cli-anything-kakaotalk", version="0.1.0", python_requires=">=3.10",
    packages=find_namespace_packages(include=["cli_anything.*"]),
    install_requires=["click>=8.1,<9", "prompt_toolkit>=3,<4"],
    package_data={"cli_anything.kakaotalk": ["bin/*", "skills/*.md", "README.md"]},
    entry_points={"console_scripts": ["cli-anything-kakaotalk=cli_anything.kakaotalk.kakaotalk_cli:main"]},
)
