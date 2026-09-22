from tallies import Todo, Task

if __name__ == "__main__":
    td = Todo("todo.txt")
    td.create_task("EPIC TASK")
    for task in td.tasks:
        print(task)