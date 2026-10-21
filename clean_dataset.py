
import pandas as pd

# Load the original dataset
df = pd.read_csv(
    "dataset/resume_dataset_200k_with_shortlisting_status.csv"
)

print("Original shape:", df.shape)

# Remove rows with invalid negative resume word counts
df_clean = df[df["resume_length_words"] >= 0].copy()

print("Cleaned shape:", df_clean.shape)
print(
    "Remaining negative values:",
    (df_clean["resume_length_words"] < 0).sum()
)

# Display target distribution
print("\nShortlisting distribution:")
print(df_clean["shortlisting_status"].value_counts())

# Save cleaned data separately
df_clean.to_csv(
    "dataset/resume_dataset_cleaned.csv",
    index=False
)

print("\nCleaned dataset saved successfully.")
