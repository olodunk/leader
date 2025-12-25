
import sys
import os

# Add current directory to path
sys.path.append(os.getcwd())

from app import get_user_rater_roles, get_examinee_role_key, RATER_RULES

def test_rater_mapping():
    print("Testing Rater Mapping...")
    
    # Case 1: Functional Dept Principal
    account = {'account_type': 'P'}
    dept = {'dept_name': '审计部', 'dept_type': '职能部门'}
    roles = get_user_rater_roles(account, dept)
    print(f"CASE 1 (Func P): Expected ['职能部门正职 (含院长助理)'], Got {roles}")
    assert '职能部门正职 (含院长助理)' in roles
    
    # Case 2: Dean's Assistant (Type L)
    account = {'account_type': 'L'}
    dept = {'dept_name': '院长助理', 'dept_type': '职能部门'} # dept_type might vary but name matches
    roles = get_user_rater_roles(account, dept)
    print(f"CASE 2 (Dean Asst L): Expected ['职能部门正职 (含院长助理)'], Got {roles}")
    assert '职能部门正职 (含院长助理)' in roles

    # Case 3: Center Principal (Lanzhou)
    account = {'account_type': 'P'}
    dept = {'dept_name': '兰州化工研究中心', 'dept_type': '两中心'}
    roles = get_user_rater_roles(account, dept)
    print(f"CASE 3 (Center P): Expected ['中心领导班子 (正职)'], Got {roles}")
    assert '中心领导班子 (正职)' in roles

    # Case 4: Kungang Branch Principal (Lanzhou)
    account = {'account_type': 'P'}
    dept = {'dept_name': '昆冈兰州分公司', 'dept_type': '分公司'}
    roles = get_user_rater_roles(account, dept)
    print(f"CASE 4 (Kungang P): Expected ['昆冈班子正职', '所属分公司班子正职'], Got {roles}")
    assert '昆冈班子正职' in roles
    assert '所属分公司班子正职' in roles

def test_examinee_mapping():
    print("\nTesting Examinee Mapping...")
    
    # Case 1: Center Principal -> Two Centers
    key = get_examinee_role_key('中心正职', '兰州化工研究中心')
    print(f"CASE 1: Expected '两中心正职', Got '{key}'")
    assert key == '两中心正职'
    
    # Case 2: Center Principal -> Branch
    key = get_examinee_role_key('中心正职', '昆冈兰州分公司')
    print(f"CASE 2: Expected '所属分公司 (兰州、抚顺) 班子正职', Got '{key}'")
    assert key == '所属分公司 (兰州、抚顺) 班子正职'

    # Case 3: Center Deputy -> Kungang Beijing
    key = get_examinee_role_key('中心副职', '昆冈公司')
    print(f"CASE 3: Expected '昆冈班子副职 (北京)', Got '{key}'")
    assert key == '昆冈班子副职 (北京)'

if __name__ == '__main__':
    try:
        test_rater_mapping()
        test_examinee_mapping()
        print("\nAll Tests Passed!")
    except AssertionError as e:
        print(f"\nTEST FAILED: {e}")
    except Exception as e:
        print(f"\nERROR: {e}")
