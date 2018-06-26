import mechanicalsoup


class TokenScraper(object):

    base_url = 'https://hypothes.is/'
    login_page_url = 'login'
    token_page_url = 'account/developer'

    username_field = 'username'
    password_field = 'password'

    generate_token_btn_text = 'generate your api token'

    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.browser = mechanicalsoup.StatefulBrowser(soup_config={'features': 'html.parser'})

    def get_api_token(self):
        self.browser.open('{0}{1}'.format(self.base_url, self.token_page_url))
        input_fields = self.browser.get_current_page().select('#token')
        if input_fields:
            api_token = input_fields[0].attrs.get('value')
            if api_token:
                return True, api_token
            else:
                return False, 'Unable to find api token in hypothesis account.'
        return False, None

    def generate_token(self):
        generate_token_btn = [btn for btn in self.browser.get_current_page().find_all('button')
                              if self.generate_token_btn_text in btn.text.lower()][:1]
        if generate_token_btn:
            self.browser.select_form('form[method="POST"]')
            self.browser.submit_selected()
            return True, None
        else:
            return False, 'Unable to generate api token in hypothesis account.'

    def login(self):
        self.browser.open('{0}{1}'.format(self.base_url, self.login_page_url))
        self.browser.select_form()
        self.browser[self.username_field] = self.username
        self.browser[self.password_field] = self.password
        response = self.browser.submit_selected()
        return self.check_login_successful(response)

    def get_token(self):
        token_found, token_message = self.get_api_token()
        if token_found:
            return token_message
        else:
            status, message = self.generate_token()
            if status:
                token_found, token_message = self.get_api_token()
                if token_found:
                    return token_message
                else:
                    raise Exception('Unknown error while getting token after login')
            else:
                raise Exception(message)

    def login_and_get_token(self):
        login_status, message = self.login()
        if login_status:
            return self.get_token()
        else:
            raise Exception(message)

    def check_login_successful(self, response):
        if response.status_code in [200, 302]:
            input_names = self.get_all_values('input', 'name')
            if self.username_field in input_names or self.password_field in input_names:
                errors = self.get_text_from_tags('li', class_='form-input__error-item')
                if [error for error in errors if ('user' in error or 'password' in error)]:
                    message = "Incorrect username or password"
                else:
                    message = "Unknown error while logging in"
            else:
                return True, None
        else:
            message = 'Unable to login to hypothesis account.'
        return False, message

    def get_all_values(self, tag, attribute):
        return [
            inp.attrs[attribute] for inp in self.browser.get_current_page().find_all(tag)
            if attribute in inp.attrs
        ]

    def get_text_from_tags(self, tag, **kwargs):
        return [
            (error_field.text or '').lower() for error_field in
            self.browser.get_current_page().find_all(tag, **kwargs)
        ]