# Load Combination Generator

This project generates load combinations from given load groups and load factors, and saves the results to a CSV file.

## Installation

1. Clone the repository:

    ```sh
    git clone <repository-url>
    cd <repository-directory>
    ```

2. Install the required dependencies using pip:

    ```sh
    pip install -r requirements.txt
    ```

## Usage

1. Prepare your `load_groups.yml` and `load_factors.yml` files with the necessary data.

2. Run the script:

    ```sh
    python main.py
    ```

3. The script will read the load groups and load factors from the YAML files, generate the load combinations, and save them to `load_combinations.csv`.

## Example

Here is an example of how to run the script:

```sh
python main.py
```

The output will look like this:

```sh
Using load groups from load_groups.yml and load factors from load_factors.yml
Number of combinations created: <number>
Load combinations saved to load_combinations.csv
Done
```
