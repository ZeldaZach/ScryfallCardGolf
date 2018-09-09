import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name='ScryfallCardGolf',
    version='0.1',
    author='Zach Halpern',
    author_email='zahalpern+pypi@gmail.com',
    description='Facilitate the Scryfall Card Golf games!',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url='https://github.com/zeldazach/scryfallcardgolf',
    packages=setuptools.find_packages(),
    license='GPL-3.0',
    classifiers=[
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)'
    ],
    keywords='Magic: The Gathering, MTG, JSON, Card Games, Collectible, Trading Cards',
    include_package_data=True,
    install_requires=[
        'requests',
        'pillow',
        'TwitterAPI',
    ],
)