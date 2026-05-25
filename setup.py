from setuptools import setup


setup(
    name="nora-local-ai",
    version="0.1.0",
    description="Nora is a local-first personal AI assistant.",
    packages=["mini_agent", "mini_agent.providers", "mini_agent.toolkits"],
    install_requires=["playwright==1.60.0"],
    entry_points={"console_scripts": ["nora=mini_agent.app:main"]},
)
