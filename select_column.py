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
    def apply_aggregation(grouped_data, columns):
        result = []
        for group_key, rows in grouped_data.items():
            aggregated_row = {}
            for column in columns:
                if column.startswith("SUM(") and column.endswith(")"):
                    col_name = column[4:-1]
                    aggregated_row[column] = sum(row[col_name] for row in rows)
                elif column.startswith("COUNT(") and column.endswith(")"):
                    col_name = column[6:-1]
                    if col_name == "*":
                        aggregated_row[column] = len(rows)
                elif column.startswith("AVG(") and column.endswith(")"):
                    col_name = column[4:-1]
                    aggregated_row[column] = sum(row[col_name] for row in rows) / len(rows)
                elif column.startswith("MAX(") and column.endswith(")"):
                    col_name = column[4:-1]
                    aggregated_row[column] = max(row[col_name] for row in rows)
                elif column.startswith("MIN(") and column.endswith(")"):
                    col_name = column[4:-1]
                    aggregated_row[column] = min(row[col_name] for row in rows)
                else:
                    aggregated_row[column] = rows[0][column]
            result.append(aggregated_row)
        return result

    def group_by(self, table_data, group_by_columns, columns):
        grouped_data = {}
        for row in table_data:
            group_key = tuple(row[column] for column in group_by_columns)
            if group_key not in grouped_data:
                grouped_data[group_key] = []
            grouped_data[group_key].append(row)
        return self.apply_aggregation(grouped_data, columns)

    def having_conditions(self, data, having_part):
        conditions = self.split_by_and(having_part)
        for cond in conditions:
            func = self.check_condition(cond)
            data = [row for row in data if func(row)]
        return data

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

    @staticmethod
    def join(left_table_data, right_table_data, left_key, right_key, join_type, selected_columns, left_table_name,
             right_table_name):
        joined_data = []
        left_columns = [f"{left_table_name}.{col}" for col in left_table_data[0].keys()]
        right_columns = [f"{right_table_name}.{col}" for col in right_table_data[0].keys()]
        all_columns = left_columns + right_columns

        def filter_columns(row):
            return [row[all_columns.index(col)] for col in selected_columns]

        if join_type == 'inner':
            for left_row in left_table_data:
                for right_row in right_table_data:
                    if left_row[left_key] == right_row[right_key]:
                        merged_row = list(left_row.values()) + list(right_row.values())
                        joined_data.append(filter_columns(merged_row))

        elif join_type == 'left':
            for left_row in left_table_data:
                matched = False
                for right_row in right_table_data:
                    if left_row[left_key] == right_row[right_key]:
                        merged_row = list(left_row.values()) + list(right_row.values())
                        joined_data.append(filter_columns(merged_row))
                        matched = True
                if not matched:
                    merged_row = list(left_row.values()) + [None] * len(right_columns)
                    joined_data.append(filter_columns(merged_row))

        elif join_type == 'right':
            for right_row in right_table_data:
                matched = False
                for left_row in left_table_data:
                    if left_row[left_key] == right_row[right_key]:
                        merged_row = list(left_row.values()) + list(right_row.values())
                        joined_data.append(filter_columns(merged_row))
                        matched = True
                if not matched:
                    merged_row = [None] * len(left_columns) + list(right_row.values())
                    joined_data.append(filter_columns(merged_row))

        elif join_type == 'full':
            matched_right = []
            for left_row in left_table_data:
                matched = False
                for right_row in right_table_data:
                    if left_row[left_key] == right_row[right_key]:
                        merged_row = list(left_row.values()) + list(right_row.values())
                        joined_data.append(filter_columns(merged_row))
                        matched_right.append(right_row)
                        matched = True
                if not matched:
                    merged_row = list(left_row.values()) + [None] * len(right_columns)
                    joined_data.append(filter_columns(merged_row))
            for right_row in right_table_data:
                if right_row not in matched_right:
                    merged_row = [None] * len(left_columns) + list(right_row.values())
                    joined_data.append(filter_columns(merged_row))
        return joined_data

    @staticmethod
    def cross_join(left_table_data, right_table_data, left_table_name, right_table_name, selected_columns):
        result = []
        left_columns = [f"{left_table_name}.{col}" for col in left_table_data[0].keys()]
        right_columns = [f"{right_table_name}.{col}" for col in right_table_data[0].keys()]
        all_columns = left_columns + right_columns

        def filter_columns(row):
            return [row[all_columns.index(col)] for col in selected_columns]

        for row1 in left_table_data:
            for row2 in right_table_data:
                merged_row = list(row1.values()) + list(row2.values())
                result.append(filter_columns(merged_row))
        return result

    def select_column(self, command):
        where_part = None
        group_by_columns = None
        having_part = None
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

        join_type = "inner"
        join_table = None
        join_condition = None

        if " JOIN " in from_part:
            if "LEFT" in from_part:
                join_type = "left"
                from_part, join_part = from_part.split(" LEFT JOIN ", 1)
            elif "RIGHT" in from_part:
                join_type = "right"
                from_part, join_part = from_part.split(" RIGHT JOIN ", 1)
            elif "FULL" in from_part:
                join_type = "full"
                from_part, join_part = from_part.split(" FULL JOIN ", 1)
            elif "CROSS" in from_part:
                join_type = "cross"
                from_part, join_part = from_part.split(" CROSS JOIN ", 1)
            else:
                from_part, join_part = from_part.split(" JOIN ", 1)

            join_table = join_part.strip()
            if join_type != "cross":
                join_table, join_condition = join_part.split(" ON ", 1)
                join_table = join_table.strip()
                join_condition = join_condition.strip()

        if " GROUP BY " in from_part:
            from_part, group_by_columns = from_part.split(" GROUP BY ", 1)
            if " HAVING " in group_by_columns:
                group_by_columns, having_part = group_by_columns.split(" HAVING ")
            group_by_columns = group_by_columns.strip().split(", ")

        if " WHERE " in from_part:
            table_name, where_part = from_part.split(" WHERE ", 1)
        else:
            table_name = from_part.split()[0]

        table_name = table_name.strip()
        if table_name not in self.tables:
            return f"Error: Table '{table_name}' not found."

        table_data = self.tables[table_name]["data"]
        table_columns = self.tables[table_name]["columns"]

        if join_table:
            if join_table not in self.tables:
                return f"Error: Table '{join_table}' not found."

            join_table_data = self.tables[join_table]["data"]
            join_table_columns = self.tables[join_table]["columns"]
            columns_left = columns_part.split(", ") if " * " not in columns_part and columns_part != "*" else [
                f"{table_name}.{col}" for col in table_columns.keys()]
            columns = columns_left
            if " * " in columns_part or columns_part == "*":
                columns_right = [f"{join_table}.{col}" for col in join_table_columns.keys()]
                columns += columns_right
            if join_type == 'cross':
                joined_data = self.cross_join(table_data, join_table_data, table_name, join_table, columns)
                return joined_data
            else:
                left_key, right_key = join_condition.split("=")
                left_key = left_key.strip()
                right_key = right_key.strip()
                table_data = self.join(table_data, join_table_data, left_key, right_key, join_type, columns, table_name,
                                       join_table)
                return table_data

        columns = columns_part.split(", ") if " * " not in columns_part and columns_part != "*" else list(
            table_columns.keys())
        if group_by_columns:
            for group_by_column in group_by_columns:
                if group_by_column not in table_columns:
                    return f"Error: Column '{group_by_column}' not found."
            table_data = self.group_by(table_data, group_by_columns, columns)

        if having_part:
            table_data = self.having_conditions(table_data, having_part)

        if order_by_column and order_by_column not in table_columns:
            return f"Error: Column '{order_by_column}' not found."

        if where_part:
            table_data = self.where_conditions(where_part, table_data)
        if order_by_column:
            table_data.sort(key=lambda x: x[order_by_column], reverse=order_desc)
        return [{col: row[col] for col in columns if col in row} for row in table_data]
