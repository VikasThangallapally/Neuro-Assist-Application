import os
import numpy as np
from tensorflow.keras.preprocessing.image import ImageDataGenerator

# Function to extract features from images
def extract_features(directory, target_size=(224, 224), batch_size=32):
    datagen = ImageDataGenerator(rescale=1./255)
    generator = datagen.flow_from_directory(
        directory,
        target_size=target_size,
        batch_size=batch_size,
        class_mode='categorical',
        shuffle=False
    )
    features = []
    labels = []
    for batch in generator:
        features.append(batch[0])
        labels.append(batch[1])
        if len(features) * batch_size >= generator.n:
            break
    features = np.vstack(features)
    labels = np.vstack(labels)
    return features, labels, generator.class_indices

# Example usage
if __name__ == "__main__":
    train_features, train_labels, class_indices = extract_features('brain tumor/Training')
    print("Features extracted:", train_features.shape)
    print("Labels shape:", train_labels.shape)
    print("Classes:", class_indices)