import json


class SelectColumn:
    def __init__(self, filename="databases/db.json"):
        self.filename = filename

        with open(self.filename, "r", encoding="utf-8") as file:
            self.tables = json.load(file)

    def execute_subquery(self, subquery):
        return self.select_column(subquery)

    def replace_subqueries(self, command):
        while "SELECT" in command:
            start_idx = command.rfind("SELECT") - 1
            subquery_end_idx = self.find_closing_bracket(command, start_idx)
            subquery = command[start_idx + 1:subquery_end_idx]
            subquery_result = self.execute_subquery(subquery)
            if isinstance(subquery_result, list):
                subquery_result = [str(row.get(list(row.keys())[0])) for row in subquery_result]
            command = command.replace(subquery, ", ".join(subquery_result))
        return command

    @staticmethod
    def find_closing_bracket(query, start_idx):
        open_brackets = 0
        for i, char in enumerate(query[start_idx:], start_idx):
            if char == "(":
                open_brackets += 1
            elif char == ")":
                open_brackets -= 1
                if open_brackets == 0:
                    return i
        return -1

    @staticmethod
    def check_condition(condition):
        operators = {
            "=": lambda x, y: x == y,
            "<>": lambda x, y: x != y,
            ">": lambda x, y: x > y,
            "<": lambda x, y: x < y,
            ">=": lambda x, y: x >= y,
            "<=": lambda x, y: x <= y,
        }

        is_not = True if "NOT" in condition else False
        condition = condition.strip()
        if is_not:
            condition = condition.replace("NOT", "").strip()
        for operator, func in operators.items():
            if f" {operator} " in condition:
                column, value = map(str.strip, condition.split(f" {operator} "))
                value = int(value) if value.isdigit() else value.strip('"').strip("'")
                base_condition = lambda row: func(int(row[column]) if str(row[column]).isdigit() else row[column],
                                                  value)
                return (lambda row: not base_condition(row)) if is_not else base_condition

        if " BETWEEN " in condition:
            column, rest = condition.split(" BETWEEN ", 1)
            if " AND " in rest:
                column = column.strip()
                start, end = map(str.strip, rest.split(" AND ", 1))
                start = int(start) if start.isdigit() else start
                end = int(end) if end.isdigit() else end
                base_condition = lambda row: start <= int(row[column]) <= end if str(
                    row[column]).isdigit() else start <= row[column] <= end
                return (lambda row: not base_condition(row)) if is_not else base_condition

        if " LIKE " in condition:
            column, pattern = map(str.strip, condition.split(" LIKE ", 1))
            pattern = pattern.strip("'").strip('"')
            if pattern.startswith("%") and pattern.endswith("%"):
                base_condition = lambda row: pattern[1:-1] in row[column]
            elif pattern.startswith("%"):
                base_condition = lambda row: row[column].endswith(pattern[1:])
            elif pattern.endswith("%"):
                base_condition = lambda row: row[column].startswith(pattern[:-1])
            else:
                base_condition = lambda row: row[column] == pattern
            return (lambda row: not base_condition(row)) if is_not else base_condition

        if " IN (" in condition:
            column, pattern = map(str.strip, condition.split(" IN ", 1))
            pattern = pattern.strip("()").split(",")
            values = [v.strip().strip('"').strip("'") for v in pattern]
            base_condition = lambda row: row[column] in values
            return (lambda row: not base_condition(row)) if is_not else base_condition

        raise ValueError(f"Error: '{condition}'")

    @staticmethod
    def split_by_and(where_part):
        parts = []
        section = []
        words = where_part.split()
        inside_between = False
        for i, word in enumerate(words):
            if word == "BETWEEN":
                inside_between = True
            if word == "AND" and not inside_between:
                parts.append(" ".join(section))
                section = []
            else:
                section.append(word)
            if inside_between and word == "AND":
                inside_between = False
        if section:
            parts.append(" ".join(section))
        return [part.strip() for part in parts]

    def where_conditions(self, where_part, table_data):
        or_conditions = where_part.split(" OR ")
        or_funks = []
        for or_part in or_conditions:
            and_conditions = self.split_by_and(or_part)
            and_funks = [self.check_condition(cond.strip()) for cond in and_conditions]
            or_funks.append(and_funks)

        def matches_row(row):
            return any(all(f(row) for f in and_fs) for and_fs in or_funks)

        return [row for row in table_data if matches_row(row)]

    def select_column(self, command):
        where_part = None
        if "SELECT" not in command or "FROM" not in command:
            return "Error: Invalid query."
        command = command[len("SELECT "):].strip().rstrip(";")
        if "SELECT" in command:
            command = self.replace_subqueries(command)
        order_by_column, order_desc = None, False
        if " ORDER BY " in command:
            command, order_by_part = command.split(" ORDER BY ")
            parts = order_by_part.split()
            order_by_column = parts[0]
            order_desc = len(parts) > 1 and parts[1] == "DESC"

        columns_part, from_part = command.split(" FROM ", 1)

        if " WHERE " in from_part:
            table_name, where_part = from_part.split(" WHERE ", 1)
        else:
            table_name = from_part.split()[0]

        table_name = table_name.strip()
        if table_name not in self.tables:
            return f"Error: Table '{table_name}' not found."

        table_data = self.tables[table_name]["data"]
        table_columns = self.tables[table_name]["columns"]

        columns = columns_part.split(", ") if "*" not in columns_part else table_columns

        if order_by_column and order_by_column not in table_columns:
            return f"Error: Column '{order_by_column}' not found."
        if where_part:
            table_data = self.where_conditions(where_part, table_data)

        if order_by_column:
            table_data.sort(key=lambda x: x[order_by_column], reverse=order_desc)

        return [{col: row[col] for col in columns if col in row} for row in table_data]
