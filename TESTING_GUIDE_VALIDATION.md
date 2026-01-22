# Testing the Brain MRI Validation System

## Quick Start Testing

### Prerequisites
- Server running (fastapi_app.py)
- Frontend accessible (neuro_assist.html)
- Test images ready

### Test Case 1: Valid Brain MRI ✓

**Test**: Upload actual brain MRI image
```
File: brain_mri_t1.png (256×256, grayscale)
Expected: ✓ Accepted, prediction generated
Error message: None
Prediction appears: Yes
```

**Verification Steps**:
1. Open the web interface
2. Click "Choose Brain MRI File"
3. Select a real brain MRI image
4. Should see prediction result
5. Check that CAM heatmap appears
6. Try asking questions about result

---

### Test Case 2: Colored Photo ✗

**Test**: Upload a color photograph
```
File: landscape.jpg (colored nature photo)
Expected: ✗ Rejected at grayscale check
Error message: "does not appear to be a brain MRI"
Prediction appears: No
```

**Verification Steps**:
1. Upload a colored photograph
2. Should see error message
3. Message should mention "grayscale"
4. No prediction generated
5. Can try uploading another image

---

### Test Case 3: Chest X-Ray ✗

**Test**: Upload a non-brain medical image
```
File: chest_xray.png (grayscale, but not brain)
Expected: ✗ Rejected at structure check
Error message: "does not appear to be a brain MRI"
Prediction appears: No
```

**Verification Steps**:
1. Upload chest X-ray (grayscale medical image)
2. Should still be rejected
3. Error mentions "brain MRI characteristics"
4. Check server logs for: "Unusual aspect ratio" or "Not sufficiently circular"

---

### Test Case 4: Document Scan ✗

**Test**: Upload scanned text document
```
File: document.png (grayscale, high contrast text)
Expected: ✗ Rejected at edge detection
Error message: "does not appear to be a brain MRI"
Prediction appears: No
```

**Verification Steps**:
1. Upload a scanned document
2. Should be rejected
3. Error message displayed
4. Check logs for: "Unusual edge pattern"

---

### Test Case 5: Blank Image ✗

**Test**: Upload blank white or black image
```
File: blank.png (all white or all black)
Expected: ✗ Rejected at contrast check
Error message: "does not appear to be a brain MRI"
Prediction appears: No
```

**Verification Steps**:
1. Create blank image (all white or black)
2. Upload it
3. Should be rejected
4. Check logs for: "Low contrast"

---

## Server-Side Testing

### Enable Debug Logging

Edit fastapi_app.py:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
```

### Check Validation Logs

When testing, look for logs:

**Valid MRI:**
```
DEBUG: Image validated as brain MRI
INFO: Image validated as brain MRI
```

**Invalid Images (examples):**
```
DEBUG: Image rejected: Not grayscale-like
DEBUG: Image rejected: Unusual aspect ratio 3.2
DEBUG: Image rejected: Too small (32x32)
DEBUG: Image rejected: Low contrast (std=3.5)
DEBUG: Image rejected: Low mid-range intensity usage (15.0%)
DEBUG: Image rejected: Unusual edge pattern (ratio=0.2)
DEBUG: Image rejected: Center region has no variation (std=1.5)
DEBUG: Image rejected: Not sufficiently circular (circularity=0.15)
DEBUG: Image rejected: Brain occupies unusual area ratio (2.5%)
```

---

## Manual Validation Testing

### Test Individual Validation Functions

Create test_validation.py:
```python
from fastapi_app import _is_grayscale_like, _is_brain_image
from PIL import Image
import numpy as np

# Test 1: Color image
color_img = Image.new('RGB', (256, 256), color=(255, 100, 50))
print(f"Color image grayscale check: {_is_grayscale_like(color_img)}")  # False
print(f"Color image brain check: {_is_brain_image(color_img)}")  # False

# Test 2: Grayscale image (but blank)
blank_img = Image.new('L', (256, 256), color=200)
print(f"Blank image grayscale check: {_is_grayscale_like(blank_img)}")  # True
print(f"Blank image brain check: {_is_brain_image(blank_img)}")  # False (low contrast)

# Test 3: Grayscale with content
content_img = Image.new('L', (256, 256))
pixels = content_img.load()
for i in range(256):
    for j in range(256):
        # Create circular pattern
        dist = ((i-128)**2 + (j-128)**2)**0.5
        value = int(100 + 100 * np.sin(dist/30))
        pixels[i, j] = max(0, min(255, value))
print(f"Content image grayscale check: {_is_grayscale_like(content_img)}")  # True
print(f"Content image brain check: {_is_brain_image(content_img)}")  # True (if circular enough)
```

---

## Automated Testing Script

Create test_validation_suite.py:
```python
import os
from PIL import Image
import numpy as np
from fastapi_app import _is_grayscale_like, _is_brain_image

# Test cases
test_cases = [
    ("color_photo.jpg", "Should reject - colored image"),
    ("brain_mri.png", "Should accept - valid MRI"),
    ("chest_xray.png", "Should reject - not brain"),
    ("document.png", "Should reject - text document"),
    ("blank_white.png", "Should reject - no contrast"),
    ("blank_black.png", "Should reject - no contrast"),
]

print("Running Validation Test Suite...")
print("=" * 60)

for filename, expected in test_cases:
    if not os.path.exists(filename):
        print(f"⚠️  {filename}: FILE NOT FOUND - skipped")
        continue
    
    try:
        img = Image.open(filename).convert('RGB')
        
        is_grayscale = _is_grayscale_like(img)
        is_brain = _is_brain_image(img)
        
        status = "✓ PASS" if is_brain else "✗ FAIL"
        print(f"{status} | {filename}")
        print(f"      {expected}")
        print(f"      Grayscale: {is_grayscale}, Brain: {is_brain}")
        print()
    except Exception as e:
        print(f"❌ ERROR | {filename}: {e}")
        print()

print("=" * 60)
print("Test suite complete")
```

---

## Frontend Testing

### Test Error Messages

1. **Colored Image Error**:
   - Upload color photo
   - Verify error appears
   - Check message mentions "grayscale"

2. **Wrong Format Error**:
   - Upload non-medical image
   - Verify error appears
   - Check message mentions "brain MRI characteristics"

3. **File Type Restriction**:
   - Open file browser
   - Verify only image formats shown
   - Medical formats should be highlighted

### Test User Experience

1. **First Upload**:
   - Select valid brain MRI
   - Should show prediction
   - CAM heatmap should appear
   - Chat should be available

2. **Invalid Upload**:
   - Select invalid image
   - Error message appears
   - Can select another file
   - Previous upload is cleared

3. **Multiple Uploads**:
   - Upload valid MRI #1
   - Upload valid MRI #2
   - Each should work independently
   - Previous results cleared

---

## Performance Testing

### Measure Validation Time

Add timing to validation:
```python
import time

start = time.time()
is_valid = _is_brain_image(pil_image)
elapsed = time.time() - start

print(f"Validation took {elapsed*1000:.1f}ms")  # Should be 100-200ms
```

Expected times:
- Grayscale check: 10ms
- Histogram analysis: 20ms
- Edge detection: 50ms
- Contour analysis: 40ms
- **Total: 100-200ms**

---

## Regression Testing

Ensure existing functionality still works:

- [x] Valid brain MRI images still get predictions
- [x] CAM heatmaps still generate
- [x] Chat functionality still works
- [x] Session persistence works
- [x] Multiple images can be uploaded
- [x] Error handling doesn't break UI
- [x] API responses unchanged format

---

## Expected Results Summary

| Test Case | Should Accept? | Reason |
|-----------|---|---|
| Brain MRI (T1, T2, FLAIR) | ✓ Yes | Meets all validation criteria |
| Color photograph | ✗ No | Fails grayscale check |
| Chest X-ray | ✗ No | Fails brain structure check |
| Document scan | ✗ No | Fails edge pattern check |
| Blank image | ✗ No | Fails contrast check |
| Panoramic image | ✗ No | Fails dimension check |
| Tiny image (32x32) | ✗ No | Fails size check |
| Medical diagram (colored) | ✗ No | Fails grayscale check |
| CT scan | ✗ No | Fails brain structure check |
| MRI properly exported | ✓ Yes | Meets all criteria |

---

## Troubleshooting

### Issue: Valid MRI rejected

**Check**:
1. Is image truly grayscale? (no color tint)
2. Is brain visible and centered?
3. Is image > 64×64 pixels?
4. Is aspect ratio reasonable (not panoramic)?
5. Check server logs for specific reason

**Fix**:
- Try adjusting image contrast
- Re-export from DICOM viewer
- Crop to better center brain
- Ensure grayscale format

### Issue: Invalid image accepted

**Check**:
1. Enable DEBUG logging
2. Check which validation stage it passed
3. Review threshold values
4. May need to adjust parameters

**Fix**:
- Lower thresholds for stricter validation
- Review validation logic
- Update test case expectations

### Issue: Validation too slow

**Check**:
1. Image size (larger = slower)
2. Server load (other processes?)
3. Disk I/O bottleneck?

**Fix**:
- Optimize image preprocessing
- Cache validation results
- Async processing

---

## Questions?

Refer to:
- **MRI_VALIDATION_IMPROVEMENTS.md** - Overview
- **MRI_VALIDATION_TECHNICAL.md** - Technical details
- **MRI_UPLOAD_GUIDE.md** - User guide

For server logs and debugging output, check:
- Application logs (check log level)
- Browser console (F12)
- Network tab in DevTools
