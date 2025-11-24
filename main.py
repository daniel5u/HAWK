# run.py
import sys
import json
import argparse
from parser import WorkflowParser, WorkflowValidationError

def main():
    parser_args = argparse.ArgumentParser(description="运行WorkflowParser")
    parser_args.add_argument("file", help="YAML 配置文件的路径 (例如: input.yml)")
    args = parser_args.parse_args()

    parser = WorkflowParser()

    try:
        result_dict = parser.parse_file(args.file)
        print(json.dumps(result_dict, indent=2, ensure_ascii=False))

    except WorkflowValidationError as e:
        print("校验失败：")
        print(e)
        sys.exit(1)
        
    except FileNotFoundError:
        print(f"错误：找不到文件")
        sys.exit(1)
        
    except Exception as e:
        print(f"系统错误：{e}")
        sys.exit(1)

if __name__ == "__main__":
    main()