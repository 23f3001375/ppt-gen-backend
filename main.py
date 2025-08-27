# main.py

from fastapi import FastAPI, HTTPException, File, UploadFile, Form, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import shutil
import tempfile
from typing import Optional

from core.llm_handler import generate_slide_content
from core.generator import create_ppt_from_template

app = FastAPI(title="Text to PowerPoint Generator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def cleanup_directory(path: str):
    """Function to remove a directory and its contents."""
    print(f"Cleaning up temporary directory: {path}")
    shutil.rmtree(path)

@app.post("/generate-ppt")
async def generate_ppt(
    background_tasks: BackgroundTasks, # Add this dependency
    text_content: str = Form(...),
    guidance: str = Form(""),
    llm_provider: str = Form(...),
    api_key: str = Form(...),
    filename: str = Form(...),
    template_file: Optional[UploadFile] = File(None)
):
    # Create a temporary directory without a 'with' block
    temp_dir = tempfile.mkdtemp()
    
    try:
        template_path = None
        if template_file:
            template_path = os.path.join(temp_dir, template_file.filename)
            with open(template_path, "wb") as buffer:
                shutil.copyfileobj(template_file.file, buffer)
        
        # 1. Generate structured slide content from LLM
        slide_data = generate_slide_content(
            text_content=text_content,
            guidance=guidance,
            llm_provider=llm_provider,
            api_key=api_key
        )
        
        if not slide_data:
            raise ValueError("LLM failed to generate slide content.")

        # 2. Create PPT with template styling
        safe_filename = f"{filename.replace(' ', '_')}.pptx"
        output_path = os.path.join(temp_dir, safe_filename)
        
        create_ppt_from_template(
            slide_data=slide_data,
            output_path=output_path,
            template_path=template_path
        )
        
        # 3. Add the cleanup task to run AFTER the response is sent
        background_tasks.add_task(cleanup_directory, temp_dir)

        # 4. Return the response. The file will exist until the download is complete.
        return FileResponse(
            path=output_path,
            media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            filename=safe_filename
        )
        
    except Exception as e:
        # If an error occurs, still clean up the directory
        cleanup_directory(temp_dir)
        print("=== Exception in /generate-ppt ===")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
    
# Add this to main.py

@app.get("/")
def read_root():
    return {"message": "Welcome to the PowerPoint Generator API! This endpoint is working."}