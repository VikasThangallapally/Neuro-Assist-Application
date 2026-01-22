# Brain MRI Upload Guide - Quick Reference

## ✅ What You CAN Upload

### Accepted Image Types:
- **Brain MRI Scans** (DICOM, NIfTI, or image export)
  - T1-weighted MRI
  - T2-weighted MRI
  - FLAIR MRI
  - Gradient echo sequences
  - Any brain MRI modality

- **File Formats**:
  - `.jpg` / `.jpeg` (JPEG grayscale images)
  - `.png` (PNG grayscale images)
  - `.tiff` / `.tif` (TIFF images)
  - `.dcm` / `.dicom` (DICOM medical format)
  - `.gif` / `.bmp` (other grayscale formats)

### Image Characteristics:
- **Color**: Grayscale or near-grayscale ONLY
- **Size**: At least 64×64 pixels
- **Shape**: Roughly square (not panoramic)
- **Content**: Brain tissue visible, not blank
- **Quality**: Good contrast, clear structures

### Example Accepted Images:
```
✓ Brain MRI slice exported as PNG (200×200, grayscale)
✓ Medical imaging software screenshot of brain scan
✓ DICOM file converted to JPEG by radiologist
✓ Brain scan from hospital PACS system exported as image
✓ Multiple brain MRI slices uploaded individually
```

## ❌ What You CANNOT Upload

### Rejected Image Types:
- ❌ Colored photographs (nature, people, objects)
- ❌ Screenshots with menus/UI elements
- ❌ CT scans of non-brain areas (chest, abdomen, spine)
- ❌ X-ray images (bones, lungs, etc.)
- ❌ Document scans (text, diagrams)
- ❌ Artistic or filtered images
- ❌ Screenshots from social media
- ❌ Logos or icons
- ❌ Blank or mostly black/white images

### Example Rejected Images:
```
✗ Landscape photograph (colored, non-medical)
✗ Person's face (colored photograph)
✗ Chest X-ray (not brain, not grayscale MRI)
✗ PDF document scanned (text heavy)
✗ Colorful medical diagram (not actual scan)
✗ Screenshot with UI elements (not pure image data)
✗ Random noise or static (no medical content)
✗ Blank white or black image (no content)
```

## Common Upload Issues

### Issue: "Image does not appear to be a brain MRI scan"

**Causes**:
- Image is in color (RGB) instead of grayscale
- Image is not a medical scan
- Image shows non-brain anatomy
- Image is too small or too large
- Image is blank or has no content

**Solution**:
1. Verify the image is a brain MRI in grayscale format
2. Convert colored images to grayscale if needed
3. Ensure the image shows brain tissue clearly
4. Try with a different brain scan
5. Check that image resolution is reasonable (64+ pixels)

### Issue: "Image dimensions unusual"

**Causes**:
- Image is panoramic (too wide)
- Image is very small (< 64 pixels)
- Image has strange aspect ratio (not square-ish)

**Solution**:
1. Crop the image to a square format
2. Increase image resolution if too small
3. Ensure width and height are similar

### Issue: "Low contrast"

**Causes**:
- Medical image is overexposed or underexposed
- Image is very dark or very bright
- Image lacks detail

**Solution**:
1. Increase contrast using image editor
2. Adjust brightness/levels
3. Try a better quality scan
4. Use original from PACS/imaging software

### Issue: "No brain structures detected"

**Causes**:
- Image shows non-brain anatomy
- Image is too noisy
- Image is a non-circular shape
- Brain isn't centered in image

**Solution**:
1. Verify image is a brain scan (not chest/spine/etc)
2. Ensure brain is centered in frame
3. Check that it's not a noisy artifact
4. Try with a different brain slice

## How to Prepare Images for Upload

### From DICOM File:
1. Open DICOM file in medical viewer (e.g., DICOM Reader, RadiAnt)
2. Set window/level to show brain clearly
3. Export as PNG or JPEG (Grayscale)
4. Save with descriptive name
5. Upload the exported image

### From Medical Software (PACS, Picture Archiving System):
1. Open the brain MRI study
2. Select a slice showing clear brain anatomy
3. Right-click → Export Image
4. Choose grayscale PNG or JPEG format
5. Upload the file

### From Existing Image:
1. Open in image editor (Photoshop, GIMP, Paint, etc)
2. Convert to Grayscale mode (Image → Mode → Grayscale)
3. Adjust contrast if needed (Image → Adjust → Levels)
4. Crop to roughly square dimensions if needed
5. Export as PNG or JPEG
6. Upload

### Best Practices:
- ✓ Use original medical imaging software exports when possible
- ✓ Keep image grayscale (don't convert to RGB)
- ✓ Use good quality scans (high resolution if available)
- ✓ Center the brain in the image frame
- ✓ Ensure good contrast (not too dark or too bright)
- ✓ Remove any labels, watermarks, or text if possible
- ✓ Use standard medical image formats

## Validation Checklist

Before uploading, verify:
- [ ] File is an actual brain MRI image
- [ ] Image is grayscale (not colored)
- [ ] File is at least 64×64 pixels
- [ ] File is roughly square-shaped (not panoramic)
- [ ] Brain area is visible and clear
- [ ] Image has good contrast (not too dark/bright)
- [ ] File format is supported (.jpg, .png, .tiff, .dcm)
- [ ] Brain structure is centered in image

## Error Messages Explained

| Error Message | Meaning | Fix |
|---|---|---|
| "Please upload a valid brain MRI image" | Image is not grayscale | Convert to grayscale format |
| "Only grayscale medical images" | Image has color | Remove color information |
| "Grayscale/near-grayscale format" | Too much color variation | Use medical imaging software to export grayscale |
| "Roughly circular brain shape" | Not brain-shaped | Ensure showing brain, not other body part |
| "Medical imaging contrast patterns" | Image quality issue | Use better quality scan |

## Support

If you continue to have upload issues:
1. Check that you're uploading a real brain MRI scan
2. Verify the image is in grayscale format
3. Try different brain MRI slices
4. Ensure image is from medical imaging software
5. Contact support with sample image if problems persist

## Privacy & Data Security

- ✓ Images are processed securely
- ✓ Data is not stored permanently
- ✓ Session-based processing
- ✓ No automatic backup to external systems
- ✓ HIPAA-compliant handling
- Always ensure you have permission to upload medical images

## Remember

⚠️ **IMPORTANT**: This is an **AI-powered analysis tool** for research and education purposes, NOT a diagnostic tool.
- Always have images reviewed by a qualified radiologist
- Don't make clinical decisions based solely on this tool
- Consult medical professionals for diagnosis
- This tool is for clinical support, not replacement
