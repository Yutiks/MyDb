import json


class InsertInto:
    def __init__(self, validate_date):
        self.filename = "databases/db.json"
        self.validate_date = validate_date
        self.tables = self.load_tables()
        self.current_table_data = []

    def load_tables(self):
        with open(self.filename, "r", encoding="utf-8") as file:
            return json.load(file)

    def save_tables(self):
        with open(self.filename, "w", encoding="utf-8") as file:
            json.dump(self.tables, file, indent=4, ensure_ascii=False)

    @staticmethod
    def parse_command(command):
        if "VALUES" not in command:
            return "Invalid command format."
        command = command.rstrip(";")
        table_part, values_part = command.split(" VALUES ")
        table_name = table_part.split()[0]

        columns = []
        if "(" in table_part:
            columns_part = table_part.split(" (", 1)[1].split(")")[0]
            columns = [col.strip() for col in columns_part.split(",")]
        values_rows = values_part.split("), (")
        return table_name, columns, values_rows

    @staticmethod
    def prepare_columns(table_columns, specified_columns):
        if specified_columns:
            for column in specified_columns:
                if column not in table_columns:
                    return f"Column '{column}' not found in table."
            return specified_columns
        return list(table_columns.keys())[1:]

    def prepare_row(self, table_columns, columns, values):
        if len(columns) != len(values):
            if len(columns) < len(values):
                raise ValueError("Number of columns and values do not match.")
            values.extend(["NULL"] * (len(columns) - len(values)))

        new_row = {}
        for column, value in zip(columns, values):
            column_spec = table_columns[column]
            self.validate_value(column, value, column_spec, new_row)
        return new_row

    def validate_value(self, column, value, column_spec, new_row):
        column_type = column_spec["type"]
        not_null = column_spec.get("not_null", False)
        unique = column_spec.get("unique", False)
        default = column_spec.get("default", None)

        if value == "NULL":
            if not_null:
                return f"Column '{column}' cannot be NULL."
            new_row[column] = default
        elif column_type == "INT":
            if not value.isdigit():
                return f"Value '{value}' is not a valid INT for column '{column}'."
            new_row[column] = int(value)
        elif column_type == "VARCHAR":
            if not (value.startswith('"') and value.endswith('"')):
                return f"Value '{value}' must be enclosed in double quotes for column '{column}'."
            value = value[1:-1]
            max_length = column_spec["max_length"]
            if len(value) > max_length:
                return f"Value '{value}' exceeds max length {max_length} for column '{column}'."
            new_row[column] = value
        elif column_type == "DATE":
            if not self.validate_date(value):
                return f"Value '{value}' is not a valid DATE (format: YYYY-MM-DD)."
            new_row[column] = value

        if unique and self.is_duplicate(column, new_row[column]):
            return f"Column '{column}' must be unique. Value '{new_row[column]}' already exists."

    def is_duplicate(self, column, value):
        for table_data in self.current_table_data:
            if table_data.get(column) == value:
                return True
        return False

    def insert_into(self, command):
        table_name, specified_columns, values_rows = self.parse_command(command[len("INSERT INTO "):])
        if table_name not in self.tables:
            return f"Table '{table_name}' does not exist."
        table_columns = self.tables[table_name]["columns"]
        primary_keys = self.tables[table_name]["primary_keys"]

        columns = self.prepare_columns(table_columns, specified_columns)
        if isinstance(columns, str):
            return columns
        self.current_table_data = self.tables[table_name]["data"]

        for row_values in values_rows:
            row_values = [value.strip() for value in row_values.strip("()").split(", ")]
            new_row = self.prepare_row(table_columns, columns, row_values)
            new_row["id"] = len(self.current_table_data) + 1
            for existing_row in self.current_table_data:
                if all(existing_row[key] == new_row.get(key) for key in primary_keys):
                    return f"Duplicate primary key found: {', '.join(f'{key}={new_row.get(key)}' for key in primary_keys)}."
            self.current_table_data.append(new_row)

        self.save_tables()
        return "Rows inserted successfully."
