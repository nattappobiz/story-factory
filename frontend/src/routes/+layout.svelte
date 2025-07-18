<!-- START OF FILE: frontend/src/routes/+layout.svelte -->
<script>
  // Import ไฟล์ CSS หลักของเราเข้ามาที่นี่
  // การทำแบบนี้จะทำให้ CSS นี้มีผลกับทุกหน้าในแอปพลิเคชัน
  import "../app.css";
</script>

<!-- 
  นี่คือ Layout หลักของแอปพลิเคชัน
  เราสามารถใส่ Header, Footer, หรือ Navbar ที่ต้องการให้มีทุกหน้าได้ที่นี่
  <slot /> คือตำแหน่งที่เนื้อหาของแต่ละหน้า (เช่น +page.svelte) จะถูกแทรกเข้ามา
-->
<div data-theme="dark" class="bg-base-200 min-h-screen">
  <slot />
</div>
<!-- END OF FILE -->