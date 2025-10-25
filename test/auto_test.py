import os

class AutoTest:
    """
    This class contains commands and instructions for running automated tests
    for the WebToReaderBackend project using pytest.
    """
    @staticmethod
    def run_tests_with_coverage():
        """
        Run tests with coverage report.
        """
        return (
            "pytest test/test.py -v --cov=app --cov-report=html --cov-report=term\n"
            "# View coverage in browser\n"
            "# Open htmlcov/index.html in your browser"
        )

    @staticmethod
    def run_specific_test_class():
        """
        Run a specific test class.
        """
        return "pytest test/test.py::TestURLValidation -v"

    @staticmethod
    def run_specific_test_method():
        """
        Run a specific test method.
        """
        return "pytest test/test.py::TestValidation::test_validate_url_valid -v"

    @staticmethod
    def run_tests_matching_pattern():
        """
        Run all tests matching a pattern.
        """
        return 'pytest test/test.py -k "url" -v'

    @staticmethod
    def run_with_pytest_module():
        """
        Run tests using the pytest module.
        """
        return "python -m pytest test/test.py -v"

    @staticmethod
    def install_test_dependencies():
        """
        Install required test dependencies.
        """
        return "pip install pytest pytest-flask pytest-cov requests-mock"

    @staticmethod
    def navigate_to_project_root():
        """
        Navigate to the project root directory.
        """
        return 'cd "C:\\Users\\Taylor\\source\\repos\\WebToReaderBackend\\web-to-reader-backend"'

    @staticmethod
    def run_tests_command():
        """
        Command to run tests.
        """
        return "pytest test/test.py -v"

    @staticmethod
    def create_init_files():
        """
        Create __init__.py files in necessary directories for package recognition.
        """
        return (
            "# In web-to-reader-backend directory\n"
            "type nul > __init__.py\n\n"
            "# In test directory\n"
            "type nul > test\\__init__.py"
        )
    
    @staticmethod
    def check_for_changes():
        """
        Check for changes in application files.
        """
        return "git ls-files -m -o --exclude-from=.gitignore"

def main():
    auto_tester = AutoTest()
    user_input = input("Run automated tests? (y/n): ").strip().lower()
    if user_input not in ['y', 'n']:
        print("Invalid input. Please enter 'y' or 'n'.")
        return
    if user_input == 'y':
        os.system(auto_tester.navigate_to_project_root())
        while True:
            if os.system(auto_tester.check_for_changes()) != "":
                os.system(auto_tester.run_tests_with_coverage())
            break
    else:
        print("Automated tests not run.")
    
if __name__ == "__main__":
    main()