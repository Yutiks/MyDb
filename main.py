from create_table import CreateTable
from delete import Delete
from insert_into import InsertInto
from select_column import SelectColumn
from update import Update


def multiline_command():
    cmd = input(">>> ")
    while not cmd.endswith(";") and cmd != "exit":
        cmd += f" {input('... ')}"
    return cmd


class MyDB:
    def __init__(self, filename="databases/db.json"):
        self.create_table = CreateTable(self.validate_date, filename)
        self.insert_into = InsertInto(self.validate_date, filename)
        self.select_column = SelectColumn(filename)
        self.delete = Delete(filename)
        self.update = Update(filename)

    @staticmethod
    def validate_date(date_str):
        parts = date_str.split("-")
        if len(parts) != 3:
            return False
        year, month, day = parts
        if not (year.isdigit() and month.isdigit() and day.isdigit()):
            return False
        year, month, day = int(year), int(month), int(day)
        return 1 <= month <= 12 and 1 <= day <= 31

    def process_command(self, command):
        if command == "exit":
            return "exit"
        elif command.startswith("INSERT INTO "):
            return self.insert_into.insert_into(command)
        elif command.startswith("CREATE TABLE "):
            return self.create_table.create_table(command)
        elif command.startswith("DELETE FROM "):
            return self.delete.delete_from(command)
        elif command.startswith("UPDATE "):
            return self.update.update(command)
        elif command.startswith("SELECT "):
            result = self.select_column.select_column(command)
            if isinstance(result, str):
                return result
            elif result:
                output = []
                for row in result:
                    if isinstance(row, list):
                        output.append(" ".join(map(str, row)))
                    elif isinstance(row, dict):
                        output.append(" ".join(map(str, row.values())))
                return "\n".join(output)
            else:
                return "No data to display."
        else:
            return "Error: Unknown command."

    def main(self):
        while True:
            command = multiline_command().strip()
            result = self.process_command(command)
            if result == "exit":
                break
            print(result)

# main()
