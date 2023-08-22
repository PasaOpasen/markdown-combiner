
- [Markdown combiner](#markdown-combiner)
- [Syntax](#syntax)
  - [**Shell** directive](#shell-directive)
  - [**Put** directive](#put-directive)
    - [Put example](#put-example)
    - [Markdown headings shift](#markdown-headings-shift)
    - [Notes](#notes)
- [Execution](#execution)


# Markdown combiner

The purpose of this python script without dependencies is to provide the functional of combining text (especially Markdown files) with 
1. Headers shifting
2. Shell commands execution

# Syntax

## **Shell** directive

Put next directive to your text file:
```js
@@echo 11@@
```

After the script execution it whole will be replaced with just *11*. U can use any commands your default shell supports.

## **Put** directive

The **put** directive will put a part of file (or a whole file content) to this command location with some postprocessing.

Put next directive:
```js
@put@../my_file.md -t@@
```

After the script execution it whole will be replaced with the content of `../my_file.md` file without empty lines at start and finish.

Between center `@` there is a command with next options:
```sh
usage: @put@ inner command parser [-h] [--start-after START_AFTER] [--ends-before END_BEFORE] [--strip]
                                  [--replace KEY=VALUE] [--allow-file-not-found]
                                  FILE [FILE ...]

positional arguments:
  FILE                  file to put, absolute path or the path relative to file contains current directive; if u put
                        several files the first existing will be chosen

options:
  -h, --help            show this help message and exit
  --start-after START_AFTER, -s START_AFTER
                        use only text after the last line contains this pattern matching (default: None)
  --ends-before END_BEFORE, -e END_BEFORE
                        use only text before the first line contains this pattern matching (default: None)
  --strip, -t           strip output text (default: False)
  --replace KEY=VALUE, -r KEY=VALUE
                        Add replacing in format like OLD=NEW. May appear multiple times (default: {})
  --allow-file-not-found, -l
                        skip commands with unknown file (default: False)
```

### Put example

Suppose u have next two files located together:

text.txt:
```
Some next to not include

next symbols are kinda a marker of the inclusion border
-----

Some text to include;
this too

##>

Don't include this message!  

```

readme.md:
```md
# About
...
# Example
start
@put@text.txt -t -s '-----' -e '##>'@@
finish
```

The translation result will be exactly this
```md
# About
...
# Example
start
Some text to include;
this too
finish
```

### Markdown headings shift

If **put** directive matches next conditions:
* is inside markdown file in the numbered section (like `### 5.4.1`)
* directives to the part of markdown with numbered sections
then the sections of included file will be shifted with the section of including file.

Example:

a.md:
```md
# 1 About

## 1.1 S1

### 1.1.1 SS

## 1.2 S2
```

b.md:
```md
# 5 Title
@put@a.md@@
```

translation result:
```md
# 5 Title
## 5.1 About

### 5.1.1 S1

#### 5.1.1.1 SS

### 5.1.2 S2
```

### Notes

In Markdown the best form for *-s* and *-e* patterns is HTML comments:
```md

# text
text

<!---START (any mark text)-->

text to select

<!---
END (multiline supports too)-->

```

# Execution

```sh
python markdown-combiner.py input_file output_file
```

This will translate command in `input_file` RECURSIVELY and save result to `output file`

More info:

```sh
python markdown-combiner.py -h
usage: markdown-combiner.py [-h] [-e] INPUT_FILE OUTPUT_FILE

Script which combines several files with shell insertions execution and special features for *.md files

positional arguments:
  INPUT_FILE            Text file to process
  OUTPUT_FILE           Path to save the output document

optional arguments:
  -h, --help            show this help message and exit
  -e, --ignore-shell-errors
                        whether to ignore errors on shell commands (default: False)
```

