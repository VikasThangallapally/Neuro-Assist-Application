import os
import sys

def test_model_loading():
    try:
        import tensorflow as tf
        if os.path.exists('models/model.h5'):
            model = tf.keras.models.load_model('models/model.h5')
            print("Model loading test: PASSED")
            return True
        else:
            print("Model loading test: FAILED - Model file not found")
            return False
    except Exception as e:
        print(f"Model loading test: FAILED - {e}")
        return False

def test_fastapi_app():
    try:
        from fastapi_app import app
        print("FastAPI app import test: PASSED")
        return True
    except Exception as e:
        print(f"FastAPI app import test: FAILED - {e}")
        return False

def test_medical_knowledge():
    try:
        from medical_knowledge import get_tumor_analysis
        result = get_tumor_analysis("Glioma", 0.95)
        if "name" in result:
            print("Medical knowledge test: PASSED")
            return True
        else:
            print("Medical knowledge test: FAILED - Invalid response")
            return False
    except Exception as e:
        print(f"Medical knowledge test: FAILED - {e}")
        return False

if __name__ == "__main__":
    tests = [test_model_loading, test_fastapi_app, test_medical_knowledge]
    passed = 0
    for test in tests:
        if test():
            passed += 1
    print(f"\nTests passed: {passed}/{len(tests)}")
    if passed == len(tests):
        print("All enhanced tests PASSED!")
    else:
        print("Some tests FAILED.")