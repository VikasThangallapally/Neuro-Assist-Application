import tensorflow as tf
import joblib

class FeatureRFModel(tf.keras.Model):
    def __init__(self, extractor=None, rf_model=None, **kwargs):
        # Accept extra kwargs (trainable, name, dtype, etc.) during deserialization
        super().__init__(**kwargs)
        # allow None defaults for deserialization paths
        self.extractor = extractor
        self.rf = rf_model

    def call(self, inputs):
        x = tf.keras.applications.efficientnet.preprocess_input(inputs)
        # extractor may be a Keras model; ensure it's callable
        feats = self.extractor(x, training=False) if self.extractor is not None else x
        # rf is a sklearn model; use numpy_function to call predict_proba
        if self.rf is not None:
            preds = tf.numpy_function(self.rf.predict_proba, [feats], tf.float32)
        else:
            # fallback: pass-through zeros
            preds = tf.zeros((tf.shape(inputs)[0], 1), dtype=tf.float32)
        return preds
