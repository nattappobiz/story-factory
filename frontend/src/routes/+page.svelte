<!-- START OF FILE: frontend/src/routes/+page.svelte (Final Version) -->
<script lang="ts">
    import { onMount } from 'svelte';
    import { quintOut } from 'svelte/easing';
    import { fade, slide } from 'svelte/transition';
    
    import { voiceOptions } from '$lib/voiceOptions.js';
    import { musicOptions } from '$lib/musicOptions.js';
    import { aspectRatioOptions } from '$lib/aspectRatioOptions.js';
    import { ageGroupOptions } from '$lib/ageGroupOptions.js';

    interface StoryLine { scene: number; text: string; emotion: string; }
    interface StoryboardItem { prompt: string; file: File | null; previewUrl: string | null; }

    let appStage: 'PROMPT' | 'STORYBOARD' | 'COMPILING' | 'DONE' = 'PROMPT';
    let isLoading: boolean = false;
    let globalErrorMessage: string = '';
    let autoGenerateImages: boolean = true;
    let userPrompt: string = 'A story about a friendly robot who learns to bake a cake.';
    let selectedAgeGroup: string = '5-7';
    let selectedVoice: string = 'en-US-Wavenet-C';
    let selectedMusic: string = 'adventure';
    let selectedAspectRatio: string = '9:16';
    let selectedMusicVolume: number = 0.3;
    let selectedTransition: string = 'fade';
    let jobId: string = '';
    let compilationStatus: string = '';
    let compilationStage: string = '';
    let checkStatusInterval: ReturnType<typeof setInterval>;
    let finalVideoUrl: string = '';
    let storyTextForDisplay: string = '';
    let storyScript: StoryLine[] = [];
    let imagePrompts: string[] = [];
    let storyboardItems: StoryboardItem[] = [];
    $: allImagesUploaded = storyboardItems.length > 0 && storyboardItems.every(item => item.file);

    async function handlePrimaryAction(): Promise<void> {
        if (autoGenerateImages) { await handleMagicCreate(); } 
        else { await handleGenerateScriptForManualUpload(); }
    }

    async function handleMagicCreate(): Promise<void> {
        if (!userPrompt.trim()) { globalErrorMessage = 'Please enter your story idea.'; return; }
        isLoading = true; globalErrorMessage = ''; appStage = 'COMPILING'; compilationStatus = 'pending'; compilationStage = '0/5: Job queued...';
        try {
            const requestBody = {
                prompt: userPrompt, age_group: selectedAgeGroup, voice_name: selectedVoice,
                music_filename: selectedMusic === 'none' ? 'none' : `${selectedMusic}.mp3`,
                aspect_ratio: selectedAspectRatio, music_volume: selectedMusicVolume, transition_style: selectedTransition,
            };
            const response = await fetch('/api/agent/create-video', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(requestBody) });
            if (!response.ok) { throw new Error((await response.json()).detail || 'Failed to start.'); }
            const data = await response.json();
            jobId = data.job_id;
            startCheckingStatus();
        } catch (error: any) {
            globalErrorMessage = error.message; appStage = 'PROMPT'; isLoading = false;
        }
    }

    async function handleGenerateScriptForManualUpload(): Promise<void> {
        if (!userPrompt.trim()) { globalErrorMessage = 'Please enter your story idea.'; return; }
        isLoading = true; globalErrorMessage = '';
        try {
            const response = await fetch('/api/manual/generate-script', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ prompt: userPrompt, image_style: 'Pixar' }) });
            if (!response.ok) { throw new Error((await response.json()).detail || 'Failed to generate story.'); }
            const data = await response.json();
            storyScript = data.story_script;
            imagePrompts = data.image_prompts;
            storyTextForDisplay = storyScript.map((line: StoryLine) => line.text).join(' ');
            storyboardItems = imagePrompts.map((prompt: string) => ({ prompt, file: null, previewUrl: null }));
            appStage = 'STORYBOARD';
        } catch (error: any) {
            globalErrorMessage = error.message;
        } finally {
            isLoading = false;
        }
    }

    function handleFileSelect(event: Event, index: number): void {
        const target = event.target as HTMLInputElement;
        const file = target.files?.[0];
        if (file) {
            storyboardItems[index].file = file;
            storyboardItems[index].previewUrl = URL.createObjectURL(file);
            storyboardItems = [...storyboardItems];
        }
    }

    async function handleManualCompile(): Promise<void> {
        isLoading = true; globalErrorMessage = ''; appStage = 'COMPILING'; compilationStage = 'Uploading files...';
        const formData = new FormData();
        formData.append('story_script_json', JSON.stringify(storyScript));
        formData.append('voice_name', selectedVoice);
        formData.append('music_filename', selectedMusic === 'none' ? 'none' : `${selectedMusic}.mp3`);
        formData.append('aspect_ratio', selectedAspectRatio);
        formData.append('music_volume', selectedMusicVolume);
        formData.append('transition_style', selectedTransition);
        storyboardItems.forEach((item, index) => { if(item.file) formData.append('images', item.file, `image_${index}.png`); });
        try {
            const response = await fetch('/api/manual/compile-video', { method: 'POST', body: formData });
            if (!response.ok) { throw new Error((await response.json()).detail || 'Failed to start.'); }
            const data = await response.json();
            jobId = data.job_id;
            startCheckingStatus();
        } catch (error: any) {
            globalErrorMessage = error.message; appStage = 'STORYBOARD'; isLoading = false;
        }
    }

    function startCheckingStatus(): void {
        clearInterval(checkStatusInterval);
        checkStatusInterval = setInterval(async () => {
            if (!jobId) return;
            try {
                const response = await fetch(`/api/jobs/${jobId}/status`); 
                if (!response.ok) { 
                    if (response.status === 404) { console.warn(`Job ${jobId} not found, retrying...`); return; }
                    throw new Error('Could not get status.');
                }
                const data = await response.json();
                compilationStatus = data.status;
                compilationStage = data.stage || 'Processing...';
                if (data.status === 'completed') {
                    finalVideoUrl = data.video_url;
                    storyTextForDisplay = data.story_text || storyTextForDisplay;
                    appStage = 'DONE'; isLoading = false; clearInterval(checkStatusInterval);
                } else if (data.status === 'failed') {
                    globalErrorMessage = `Process failed: ${data.error || 'Unknown error'}`;
                    appStage = 'PROMPT'; isLoading = false; clearInterval(checkStatusInterval);
                }
            } catch (error: any) {
                globalErrorMessage = 'Error checking status.'; isLoading = false; clearInterval(checkStatusInterval); appStage = 'PROMPT';
            }
        }, 3000);
    }

    function resetApp(): void {
        appStage = 'PROMPT'; isLoading = false; jobId = ''; finalVideoUrl = ''; globalErrorMessage = '';
        storyboardItems = []; clearInterval(checkStatusInterval);
    }
    
    onMount(() => { return () => clearInterval(checkStatusInterval); });
</script>

<div class="container mx-auto p-4 md:p-8 max-w-4xl">
    <header class="text-center mb-8 md:mb-12" in:fade={{ duration: 500 }}>
        <h1 class="text-4xl md:text-5xl font-bold mb-2">✨ AI Story Factory ✨</h1>
        <p class="text-lg text-base-content/70">Turn your ideas into animated stories in minutes.</p>
    </header>

    {#if globalErrorMessage}
        <div role="alert" class="alert alert-error shadow-lg mb-8" transition:slide>
            <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2 2m2-2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
            <span>Error: {globalErrorMessage}</span>
            <button class="btn btn-sm btn-ghost" on:click={() => globalErrorMessage = ''}>Dismiss</button>
        </div>
    {/if}

    {#if appStage === 'PROMPT'}
        <div class="card bg-base-100 shadow-xl" in:fade|global>
            <div class="card-body p-6 md:p-8">
                <div class="form-control">
                    <label class="label" for="user-prompt"><span class="label-text text-xl font-semibold">1. What's Your Story?</span></label>
                    <textarea id="user-prompt" bind:value={userPrompt} class="textarea textarea-bordered textarea-lg w-full h-32" placeholder="e.g., A brave knight goes on a quest..."></textarea>
                </div>
                
                <div class="form-control w-fit my-6 bg-base-200 p-2 rounded-lg">
                    <label class="label cursor-pointer gap-4">
                        <span class="label-text text-lg">Automatically generate images</span> 
                        <input type="checkbox" class="toggle toggle-primary" bind:checked={autoGenerateImages} />
                    </label>
                </div>

                <h2 class="text-xl font-semibold">2. Choose Your Settings</h2>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mt-2">
                    <div class="form-control w-full">
                        <label class="label" for="age-group"><span class="label-text">Target Audience</span></label>
                        <select id="age-group" class="select select-bordered" bind:value={selectedAgeGroup}>
                            {#each ageGroupOptions as option} <option value={option.value}>{option.label}</option> {/each}
                        </select>
                    </div>
                     <div class="form-control w-full">
                        <label class="label" for="aspect-ratio"><span class="label-text">Aspect Ratio</span></label>
                        <select id="aspect-ratio" class="select select-bordered" bind:value={selectedAspectRatio}>
                            {#each aspectRatioOptions as option} <option value={option.value}>{option.label}</option> {/each}
                        </select>
                    </div>
                    <div class="form-control w-full">
                        <label class="label" for="voice-actor"><span class="label-text">Voice Actor</span></label>
                        <select id="voice-actor" class="select select-bordered" bind:value={selectedVoice}>
                            {#each voiceOptions as option} <option value={option.value}>{option.label}</option> {/each}
                        </select>
                    </div>
                    <div class="form-control w-full">
                        <label class="label" for="music-track"><span class="label-text">Music Track</span></label>
                        <select id="music-track" class="select select-bordered" bind:value={selectedMusic}>
                            {#each musicOptions as option} <option value={option.value}>{option.label}</option> {/each}
                        </select>
                    </div>
                </div>

                <div class="card-actions justify-end mt-8">
                    <button class="btn btn-primary btn-lg" on:click={handlePrimaryAction} disabled={isLoading}>
                        {#if isLoading} <span class="loading loading-spinner"></span> {/if}
                        {#if autoGenerateImages} ✨ Create Full Video! {:else} 📝 Generate Storyboard {/if}
                    </button>
                </div>
            </div>
        </div>
    {/if}

    {#if appStage === 'STORYBOARD'}
        <div class="card bg-base-100 shadow-xl" in:slide|global>
            <div class="card-body p-6 md:p-8">
                <h2 class="card-title text-2xl">3. Build Your Storyboard</h2>
                <div class="p-4 bg-base-200 rounded-lg my-4">
                    <h3 class="font-bold">Story Summary:</h3>
                    <p class="text-base-content/80 whitespace-pre-wrap">{storyTextForDisplay}</p>
                </div>
                
                <div class="space-y-6">
                    {#each storyboardItems as item, index}
                        <div class="card card-compact bg-base-200">
                            <div class="card-body">
                                <p><strong>Scene {index + 1}:</strong> {item.prompt}</p>
                                <div class="mt-2">
                                    <input type="file" id="file-{index}" class="file-input file-input-bordered file-input-sm w-full max-w-xs" accept="image/*" on:change={(e) => handleFileSelect(e, index)}>
                                </div>
                                {#if item.previewUrl}
                                    <figure class="mt-4"><img src={item.previewUrl} alt="Preview for scene {index+1}" class="rounded-lg max-h-48 w-auto"></figure>
                                {/if}
                            </div>
                        </div>
                    {/each}
                </div>
                
                {#if allImagesUploaded}
                    <div class="card-actions justify-end mt-8" transition:fade>
                        <button class="btn btn-primary btn-lg" on:click={handleManualCompile} disabled={isLoading}>
                            {#if isLoading} <span class="loading loading-spinner"></span> {/if}
                            Compile Final Video!
                        </button>
                    </div>
                {/if}
            </div>
        </div>
    {/if}

    {#if appStage === 'COMPILING'}
        <div class="card bg-base-100 shadow-xl text-center" in:fade|global>
            <div class="card-body items-center p-6 md:p-8">
                <h2 class="card-title text-3xl">Creating Your Masterpiece...</h2>
                <p class="text-base-content/70 mt-2">Please wait, the AI is working its magic!</p>
                <span class="loading loading-dots loading-lg my-8"></span>
                <div class="w-full max-w-md space-y-2">
                    <p class="font-semibold text-lg">{compilationStage}</p>
                    <progress class="progress progress-primary w-full" value={compilationStage.split('/')[0]} max={compilationStage.split('/')[1] || 5}></progress>
                </div>
            </div>
        </div>
    {/if}

    {#if appStage === 'DONE'}
        <div class="card bg-base-100 shadow-xl text-center" in:fade|global>
            <div class="card-body items-center p-6 md:p-8">
                <h2 class="card-title text-3xl">✨ Your Video is Ready! ✨</h2>
                <figure class="my-6 w-full max-w-2xl">
                    <!-- svelte-ignore a11y-media-has-caption -->
                    <video class="rounded-lg shadow-md" controls src={finalVideoUrl} playsinline></video>
                </figure>
                <div class="card-actions">
                    <a href={finalVideoUrl} download="ai_story_video.mp4" class="btn btn-primary btn-lg">Download Video</a>
                    <button class="btn btn-ghost btn-lg" on:click={resetApp}>Create Another Story</button>
                </div>
            </div>
        </div>
    {/if}
</div>
<!-- END OF FILE -->