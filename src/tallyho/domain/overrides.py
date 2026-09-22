from enum import Enum
import re
from typing import override

import tallies  # pyright: ignore[reportMissingTypeStubs]

class Period(Enum):
    SECOND = "s"
    MINUTE = "m"
    HOUR = "h"
    DAY = "d"
    WEEK = "w"
    MONTH = "M"
    YEAR = "y"

class Weekday(Enum):
    MONDAY = "M"
    TUESDAY = "T"
    WEDNESDAY = "W"
    THURSDAY = "H"
    FRIDAY = "F"

class Length:
    def __init__(
        self,
        interval: int,
        period: Period
    ) -> None:
        self.interval: int = interval
        self.period: Period = period
    
    @override
    def __str__(self) -> str:
        return f"{self.interval}{self.period.value}"

class Recurrence:
    def __init__(
        self,
        domain: Length | list[Weekday],
        start: str | None = None,
        end: str = "0"
    ) -> None:
        self.domain: Length | list[Weekday] = domain
        self.start: str = start if start else tallies.get_current_date()
        self.end: str = end
    
    @override
    def __str__(self) -> str:
        out: str = ""
        if isinstance(self.domain, Length):
            out += f"r:{self.domain.interval}{self.domain.period.value} "
        else:
            weekdays: list[str] = [w.value for w in self.domain]
            out += f"r:{"".join(weekdays)} "

        out += f"start:{self.start} "
        out += f"end:{self.end}"

        return out

class Todo:
    tasks: list[Task] = []
    
    def __init__(self, file: str) -> None:
        self.file: str = file

        with open(file, "r") as f:
            for line in f.readlines():
                parse: Task | None = self._parse_line(line)
                if parse:
                    self.add_task(parse)
    
    def _save(self) -> None:
        with open(self.file, "w") as f:
            for task in self.tasks:
                _ = f.write(str(task) + "\n")

    def _parse_line(self, line: str) -> Task | None:
        task: Task = Task("")

        parts: list[str] = line.split()
        
        # Is the task completed
        if parts[0] == "x":
            task.completed = True
            _ = parts.pop(0)
        
        # Is the task prioritized
        if "(" in parts[0]:
            if parts[0][1].isupper() and parts[0][1].isalpha():
                task.priority = tallies.Priority[parts[0][1]]
            _ = parts.pop(0)

        # If it has 1 date, assume creation date, if it has 2 dates, it is both 
        date1_match: re.Match[str] | None = re.match(r"\d{4}-\d{2}-\d{2}", parts[0])
        date2_match: re.Match[str] | None = re.match(r"\d{4}-\d{2}-\d{2}", parts[1])

        # If two dates
        if date1_match and date2_match:
            task.completion_date = parts[0]
            task.creation_date = parts[1]
            _ = parts.pop(0)
            _ = parts.pop(0)
        
        # If one date
        elif date1_match and date2_match is None:
            task.creation_date = parts[0]
            _ = parts.pop(0)
        
        # What projects are specified
        projects: list[str] = re.findall(r"\+(\S+)", line)
        if projects:
            for proj in projects:
                task.projects.append(proj)
                _ = parts.remove("+" + proj)

        # What contexts are specified
        contexts: list[str] = re.findall(r"@(\S+)", line)
        if contexts:
            for ctx in contexts:
                task.contexts.append(ctx)
                _ = parts.remove("@" + ctx)
        
        # What special tags are specified
        tags: dict[str, str] = {}
        tags_list: list[str] = re.findall(r"([^\s:]+):(\S+)", line)
        links: list[str] = []
        for tag in tags_list:
            # Check for links
            if tag[0] == "link":
                links.append(tag[1])
            else:
                tags[tag[0]] = tag[1]
            
            _ = parts.remove(tag[0] + ":" + tag[1])
        
        # Sort through tags for extension keywords
        final_tags: dict[str, str] = {}
        for key, value in tags.items():
            match key:
                case "due":
                    task.due = value
                case "t":
                    task.threshold = value
                case "r":
                    digits: str = ""
                    for char in value:
                        if char.isdigit():
                            digits += char
                    
                    if len(digits) > 0:
                        task.recurrence = Recurrence(
                            Length(
                                int(digits),
                                Period(value[len(digits):])
                            ),
                            tags["start"],
                            tags["end"]
                        )
                    else:
                        weekdays = [Weekday(char) for char in list(value)]
                        task.recurrence = Recurrence(
                            weekdays,
                            tags["start"],
                            tags["end"]
                        )
                case "len":
                    digits_l: str = ""
                    for char in value:
                        if char.isdigit():
                            digits_l += char
                    
                    task.length = Length(
                        int(digits_l),
                        Period(value[len(digits_l):])
                    )
                case "d":
                    task.difficulty = float(value)
                case "start":
                    pass
                case "end":
                    pass
                case _:
                    final_tags[key] = value

        task.tags = final_tags

        # Description
        if "|" in parts:
            total: str = " ".join(parts)
            desc, details = total.split("|")
            task.desc = desc
            task.details = details
        else:
            task.desc = " ".join(parts)

        return task

    def add_task(self, task: Task) -> None:
        self.tasks.append(task)
        self._save()

    def create_task(
        self,
        desc: str = "Task",
        creation_date: str | None = None,
        completion_date: str | None = None,
        priority: tallies.Priority | None = None,
        projects: list[str] | None = None,
        contexts: list[str] | None = None,
        tags: dict[str, str] | None = None,
        completed: bool = False,
        due: str | None = None,
        threshold: str | None = None,
        recurrence: Recurrence | None = None,
        length: Length | None = None,
        difficulty: float | None = None,
        details: str | None = None,
        links: list[str] | None = None
    ) -> Task:
        task = Task(
            desc,
            creation_date,
            completion_date,
            priority,
            projects,
            contexts,
            tags,
            completed,
            due,
            threshold,
            recurrence,
            length,
            difficulty,
            details,
            links
        )
        
        self.tasks.append(task)
        self._save()
        return task
    
    def complete_task_by_index(self, index: int) -> None:
        self.tasks[index].complete_task()
        self._save()
    
    def complete_task(self, task: Task) -> None:
        task.complete_task()
        self._save()
        
    def search_by_desc(self, query: str, case_sensitive: bool = False) -> list[Task] | None:
        result: list[Task] = [task for task in self.tasks if query in task.desc] if case_sensitive \
                        else [task for task in self.tasks if query.upper() in task.desc.upper()]
        return sorted(result, key=lambda t: t.desc)

class Task(tallies.Task):
    def __init__(
        self,
        desc: str,
        creation_date: str | None = None,
        completion_date: str | None = None,
        priority: tallies.Priority | None = None,
        projects: list[str] | None = None,
        contexts: list[str] | None = None,
        tags: dict[str, str] | None = None,
        completed: bool = False,
        due: str | None = None,
        threshold: str | None = None,
        recurrence: Recurrence | None = None,
        length: Length | None = None,
        difficulty: float | None = None,
        details: str | None = None,
        links: list[str] | None = None
    ) -> None:
        super().__init__(desc, creation_date, completion_date, priority, projects, contexts, tags, completed)
        self.due: str | None = due
        self.threshold: str | None = threshold
        self.recurrence: Recurrence | None = recurrence
        self.length: Length | None = length
        self.difficulty: float | None = difficulty
        self.details: str | None = details
        self.links: list[str] | None = links
    
    @override
    def __str__(self) -> str:
        out: str = super().__str__()

        out += f" due:{self.due} " if self.due else ""

        out += f"t:{self.threshold} " if self.threshold else ""

        if self.recurrence:
            out += str(self.recurrence) + " "

        out += f"len:{self.length} " if self.length else ""

        out += f"d:{self.difficulty} " if self.difficulty else ""

        if self.links:
            for link in self.links:
                out += f"link:{link} "
        
        desc_loc = out.find(self.desc) + len(self.desc)
        out = out[:desc_loc].strip() + " | " + self.details.strip() + " " + out[desc_loc:].strip() + " " if self.details else out

        return out

if __name__ == "__main__":
    td = Todo("todo.txt")

    # t1 = Task("Do something cool but i did it", priority=tallies.Priority.A, completed=False, projects=["project"], contexts=["context"])
    # t = Task("Do something cool but i did it", priority=tallies.Priority.A, 
    #     completed=False,
    #     projects=["project"],
    #     contexts=["context"],
    #     due="2026-09-23",
    #     details="A cool description and this is the end.\\njust kidding here's a new line!",
    #     threshold="2026-09-20",
    #     difficulty=0.7,
    #     links=["https://google.com", "https://example.com"],
    #     length=Length(4, Period.MONTH),
    #     # recurrence=Recurrence([Weekday.MONDAY, Weekday.WEDNESDAY])
    #     recurrence=Recurrence(Length(5, Period.DAY), start="2026-09-21", end="2026-09-22")
    # )
    # print(t1)
    # print(t)

    # td.add_task(t1)
    # td.add_task(t)

    for task in td.tasks:
        print(task)
