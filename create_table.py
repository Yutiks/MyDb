import json


class CreateTable:
    def __init__(self, validate_date, filename="databases/db.json"):
        self.filename = filename
        self.validate_date = validate_date
        self.tables = self.load_tables()

    def load_tables(self):
        try:
            with open(self.filename, "r", encoding="utf-8") as file:
                return json.load(file)
        except FileNotFoundError:
            return {}

    def parse_column(self, column):
        column_parts = column.split()
        if len(column_parts) < 2:
            return None
        column_name = column_parts[0]
        column_type = column_parts[1]
        not_null = "NOT NULL" in column
        unique = "UNIQUE" in column
        is_primary_key = "PRIMARY KEY" in column
        is_foreign_key = "FOREIGN KEY" in column
        references_table = None
        references_column = None

        if is_foreign_key and "REFERENCES" in column:
            try:
                ref_idx = column_parts.index("REFERENCES") + 1
                references_table, references_column = column_parts[ref_idx].split("(")
                references_column = references_column.rstrip(")")
            except (IndexError, ValueError):
                return f"Error: Invalid FOREIGN KEY format in column '{column_name}'."
        default_value = self.parse_default_value(column_parts, column_name, column_type)
        return (
            column_name, column_type, not_null, unique,
            is_primary_key, is_foreign_key, references_table, references_column, default_value
        )

    def parse_default_value(self, column_parts, column_name, column_type):
        if "DEFAULT" not in column_parts:
            return None
        try:
            default_index = column_parts.index("DEFAULT") + 1
            default_value = column_parts[default_index]
            return self.validate_default_value(column_type, default_value)
        except (IndexError, ValueError):
            return f"Error: Invalid DEFAULT value for column '{column_name}'."

    def validate_default_value(self, column_type, default_value):
        if column_type == "VARCHAR" and not (default_value.startswith('"') and default_value.endswith('"')):
            raise ValueError(f"Error: Default value '{default_value}' must be enclosed in double quotes for VARCHAR.")
        if column_type == "INT" and not default_value.isdigit():
            raise ValueError(f"Error: Default value '{default_value}' is not a valid INT.")
        else:
            default_value = int(default_value)
        if column_type == "DATE" and not self.validate_date(default_value):
            raise ValueError(f"Error: Default value '{default_value}' is not a valid DATE (format: YYYY-MM-DD).")
        if column_type == "VARCHAR":
            raise ValueError(default_value[1:-1])
        return default_value

    def validate_column_type(self, column_name, column_type):
        if column_type.startswith("VARCHAR"):
            return self.validate_varchar_type(column_name, column_type)
        elif column_type == "INT":
            return {"type": "INT"}
        elif column_type == "DATE":
            return {"type": "DATE"}
        return f"Error: Unsupported data type '{column_type}' in column '{column_name}'."

    @staticmethod
    def validate_varchar_type(column_name, column_type):
        if not column_type.endswith(")"):
            return f"Error: Invalid format for VARCHAR in column '{column_name}'."
        try:
            max_length = int(column_type[8:-1])
            return {"type": "VARCHAR", "max_length": max_length}
        except ValueError:
            return f"Error: Invalid format for VARCHAR in column '{column_name}'."

    def create_table(self, command):
        command = command[len("CREATE TABLE "):]
        table_name, columns = command.split("(", 1)
        table_name = table_name.split()[0]
        columns = columns[:-2].split(", ")
        if not columns or not table_name:
            return "Error: Invalid command format."
        table_columns = {}
        primary_keys = []
        foreign_keys = []
        for column in columns:
            (
                column_name, column_type, not_null, unique,
                is_primary_key, is_foreign_key, references_table, references_column, default_value
            ) = self.parse_column(column)
            column_type_validation = self.validate_column_type(column_name, column_type)

            if isinstance(self.parse_column(column), str):
                return self.parse_column(column)

            table_columns[column_name] = {
                "type": column_type_validation["type"],
                "max_length": column_type_validation.get("max_length"),
                "not_null": not_null,
                "unique": unique,
                "default": default_value,
            }
            if is_primary_key:
                primary_keys.append(column_name)
            if is_foreign_key:
                try:
                    parent_table = self.tables[references_table]
                    parent_columns = parent_table["columns"]
                    is_primary = references_column in parent_table["primary_keys"]
                    is_unique = parent_columns.get(references_column, {}).get("unique", False)
                    if is_primary or is_unique:
                        foreign_keys.append({
                            "column": column_name,
                            "references_table": references_table,
                            "references_column": references_column
                        })
                        if "related_tables" not in parent_table:
                            parent_table["related_tables"] = []
                        parent_table["related_tables"].append({
                            "table": table_name,
                            "column": column_name
                        })
                    else:
                        return f"Error: Cannot reference column '{references_column}' in table '{references_table}' — it must be PRIMARY KEY or UNIQUE."

                except KeyError:
                    return f"Error: Table '{references_table}' or column '{references_column}' does not exist."
        if not primary_keys:
            return "Error: No PRIMARY KEY specified."
        if table_name in self.tables:
            return f"Error: Table '{table_name}' already exists."

        self.tables[table_name] = {
            "columns": table_columns,
            "primary_keys": primary_keys,
            "foreign_keys": foreign_keys,
            "data": []
        }
        with open(self.filename, "w", encoding="utf-8") as file:
            json.dump(self.tables, file, indent=4, ensure_ascii=False)
        return f"Table '{table_name}' created successfully."
