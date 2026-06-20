import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv(
    "reports/cnn_results.csv"
)

# MAE comparison

plt.figure(figsize=(12,6))

plt.plot(
    df["Frequency"],
    df["Raw_MAE"],
    marker="o",
    label="Raw"
)

plt.plot(
    df["Frequency"],
    df["CNN_MAE"],
    marker="o",
    label="CNN"
)

plt.xlabel("Frequency (Hz)")
plt.ylabel("MAE")

plt.title(
    "MAE Comparison"
)

plt.legend()

plt.grid(True)

plt.savefig(
    "figures/mae_comparison.png",
    dpi=300
)

plt.close()

# RMSE comparison

plt.figure(figsize=(12,6))

plt.plot(
    df["Frequency"],
    df["Raw_RMSE"],
    marker="o",
    label="Raw"
)

plt.plot(
    df["Frequency"],
    df["CNN_RMSE"],
    marker="o",
    label="CNN"
)

plt.xlabel("Frequency (Hz)")
plt.ylabel("RMSE")

plt.title(
    "RMSE Comparison"
)

plt.legend()

plt.grid(True)

plt.savefig(
    "figures/rmse_comparison.png",
    dpi=300
)

plt.close()

print(
    "Figures generated."
)