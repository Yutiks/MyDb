import create_table
import insert_into
import select_column


class MyDB:
    def __init__(self):
        self.create_table = create_table.CreateTable(self.validate_date)
        self.insert_into = insert_into.InsertInto(self.validate_date)
        self.select_column = select_column.SelectColumn()

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


def main():
    db = MyDB()

    def multiline_command():
        cmd = input(">>> ")
        while not cmd.endswith(";") and cmd != "exit":
            cmd += f" {input('... ')}"
        return cmd

    while True:
        command = multiline_command().strip()
        if command == "exit":
            break
        elif command.startswith("INSERT INTO "):
            print(db.insert_into.insert_into(command))
        elif command.startswith("CREATE TABLE "):
            print(db.create_table.create_table(command))
        elif command.startswith("SELECT "):
            result = db.select_column.select_column(command)
            if isinstance(result, str):
                print(result)
            elif result:
                for row in result:
                    print(*row.values())
            else:
                print("No data to display.")
        else:
            print("Error: Unknown command.")


main()
