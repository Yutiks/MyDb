from select_column import SelectColumn, json


class Delete:
    def __init__(self, filename="databases/db.json"):
        self.filename = filename
        self.select = SelectColumn(self.filename)
        with open(self.filename, "r", encoding="utf-8") as file:
            self.tables = json.load(file)

    def delete_from(self, command):
        command = command[len("DELETE FROM "):].rstrip(";").strip()

        if " WHERE " not in command:
            return "Error: Condition is required. Use 'WHERE'."

        table_name, where_part = command.split(" WHERE ")
        table_name = table_name.strip()

        if table_name not in self.tables:
            return f"Table '{table_name}' does not exist."

        table_data = self.tables[table_name]["data"]
        where_part = self.select.replace_subqueries(where_part)
        condition_func = self.select.check_condition(where_part)

        filtered_data = [row for row in table_data if not condition_func(row)]
        deleted_count = len(table_data) - len(filtered_data)
        self.tables[table_name]["data"] = filtered_data

        with open(self.filename, "w", encoding="utf-8") as file:
            json.dump(self.tables, file, indent=4, ensure_ascii=False)

        return f"Deleted {deleted_count} record(s) from table '{table_name}'."
