import {defineConfig} from '@playwright/test';
export default defineConfig({testDir:'./tests',use:{headless:true,viewport:{width:1440,height:1000},launchOptions:process.env.CALODETECT_TEST_BROWSER?{executablePath:process.env.CALODETECT_TEST_BROWSER}:{}}});
