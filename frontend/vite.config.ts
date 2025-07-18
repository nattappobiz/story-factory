// --- START OF FILE: frontend/vite.config.ts (Final Version) ---
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [sveltekit()],

	// --- [เพิ่ม] ส่วนของการตั้งค่า Server และ Proxy ---
	server: {
		// กำหนด Port สำหรับ Dev Server (ถ้าต้องการ)
		// port: 5173, 

		// นี่คือหัวใจของการเชื่อมต่อ Frontend กับ Backend
		proxy: {
			// ถ้ามี Request ใดๆ ก็ตามที่ URL path ขึ้นต้นด้วย '/api'
			'/api': {
				// ให้ส่ง Request นั้นต่อไปยัง Backend Server ของเราที่รันอยู่ที่ Port 8000
				target: 'http://localhost:8000',
				
				// เปลี่ยน Origin header ของ request ให้ตรงกับ target
				// ซึ่งสำคัญมากสำหรับการทำงานของ API ส่วนใหญ่
				changeOrigin: true,
			}
		}
	}
});
// --- END OF FILE ---