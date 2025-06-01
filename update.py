from select_column import SelectColumn, json


class Update:
    def __init__(self, filename="databases/db.json"):
        self.filename = filename
        self.select = SelectColumn(self.filename)
        with open(self.filename, "r", encoding="utf-8") as file:
            self.tables = json.load(file)

    def find_indices(self, table_data, condition):
        condition_func = self.select.check_condition(condition)
        return [i for i, row in enumerate(table_data) if condition_func(row)]

    def update(self, command):
        if " SET " not in command or " WHERE " not in command:
            return "Error: Invalid query."

        command = command[len("UPDATE "):].rstrip(";")
        table_name, rest = command.split(" SET ", 1)
        table_name = table_name.strip()

        if table_name not in self.tables:
            return f"Error: Table '{table_name}' not found."

        set_part, where_part = rest.split(" WHERE ", 1)
        updates = {key.strip(): value.strip().strip('"').strip("'") for key, value in
                   (part.split("=") for part in set_part.split(", "))}
        table_data = self.tables[table_name]["data"]

        for column in updates:
            if column not in self.tables[table_name]["columns"]:
                return f"Error: Column '{column}' not found."

        where_part = self.select.replace_subqueries(where_part)
        indices_to_update = self.find_indices(table_data, where_part)

        for i in indices_to_update:
            for column, value in updates.items():
                old_value = table_data[i][column]
                column_info = self.tables[table_name]["columns"].get(column)
                value = type(old_value)(value)
                if column_info.get("unique") or column in self.tables[table_name]["primary_keys"]:
                    if any(row[column] == value for row in table_data if row != table_data[i]):
                        return f"Error: The value '{value}' already exists in column '{column}'."
                table_data[i][column] = value

                if column in self.tables[table_name]["primary_keys"]:
                    self.update_foreign_keys(table_name, old_value, table_data[i][column])

        with open(self.filename, "w", encoding="utf-8") as file:
            json.dump(self.tables, file, ensure_ascii=False, indent=4)

        return "Query executed successfully."

    def update_foreign_keys(self, parent_table, old_value, new_value):
        related_tables = self.tables[parent_table].get("related_tables", [])
        for related in related_tables:
            related_table = related["table"]
            related_column = related["column"]
            if related_table in self.tables:
                for row in self.tables[related_table]["data"]:
                    if row.get(related_column) == old_value:
                        row[related_column] = new_value
