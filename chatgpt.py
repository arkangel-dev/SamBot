import undetected_chromedriver as uc
import logging
import time
import asyncio

from typing import Tuple
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException

class ChatGpt:
    
    driver: uc.Chrome = None

    def __init__(self, username:str, password:str) -> None:
        self._setupLogging()
        self._username = username
        self._password = password
        self.logger.info('Setting up Undetected Chrome Driver')
        options = Options()
        options.add_argument('--headless')
        self.driver = uc.Chrome(headless=True, use_subprocess=True, options=options)
        self.logger.info('Undetected Chrome Driver setup complete')

    '''
    Setup the logging. Print to console
    '''
    def _setupLogging(self):
        self.logger: logging.Logger = logging.getLogger('chatgpt')
        self.logger.setLevel(logging.DEBUG)
        ch = logging.StreamHandler()
        ch.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(ch)

    def _waitForElement(self, by:str, elementid:str):
        element = WebDriverWait(self.driver, 300).until(
            EC.visibility_of_element_located((by, elementid))
        )
        return element

    def _locateElement(self, by:str, elem:str):
        try:
            return self.driver.find_element(by=by, value=elem)
        except NoSuchElementException:
            return None

    def _waitForElementToDisappear(self, by:str, elem:str):
        WebDriverWait(self.driver, 300).until(
            EC.invisibility_of_element((by, elem))
        )

    def Login(self):

        self.logger.debug('Starting login sequence')
        self.driver.get('https://chatgpt.com/')

        time.sleep(5000)
        print(self.driver.get_screenshot_as_base64())
        self._waitForElement(By.ID, 'prompt-textarea')
        self.logger.debug('Page loaded')

        login_button = self._locateElement(By.XPATH, '//button[@data-testid="login-button"]')
        if not login_button:
            self.logger.info('Login button not on page. Assuming we are logged in')
            return 
        self.logger.info('Starting login')
        login_button.click()
        
        continue_button = self._waitForElement(By.XPATH, '//button[@class="continue-btn"]')
        self.logger.debug('Login page loaded')
        self.logger.debug('Entering username')
        email_box = self._waitForElement(By.ID, 'email-input')
        email_box.send_keys(self._username)
        continue_button.click()

        self.logger.debug('Entering password')
        password_box = self._waitForElement(By.ID, 'password')
        password_box.send_keys(self._password)
        continue_button = self._waitForElement(By.XPATH, '//button[@type="submit"]')
        continue_button.click()
        self.logger.debug('Done. Waiting for prompt to load')
        self._waitForElement(By.ID, 'prompt-textarea')
        self.logger.info('Login successful')

    def Prompt(self, prompt:str):
        prompt = prompt.replace('\n', '\\n')
        prompt = prompt.replace('"', "'")
        self.driver.execute_script(f'document.getElementById("prompt-textarea").value="{prompt}";')
        
        prompt_element = self._locateElement(By.ID, 'prompt-textarea')
        prompt_element.send_keys('\n')
        time.sleep(2)
        send_button = self._locateElement(By.XPATH, '//button[@data-testid="send-button"]')
        send_button.click()

        self._waitForElementToDisappear(By.XPATH, '//button[@data-testid="send-button"]')
        self._waitForElementToDisappear(By.XPATH, '//button[@data-testid="stop-button"]')
        time.sleep(2)
        return self._locateElement(By.XPATH, '(//div[@data-message-author-role="assistant"])[last()]').text
        
    async def PromptAsync(self, prompt:str):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.Prompt, prompt)


        