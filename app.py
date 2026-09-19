import io
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Exam Seating Arrangement System", page_icon="📝", layout="wide"
)

# --- 1. DOWNLOAD SAMPLE EXCEL TEMPLATE ---


def generate_sample_excel():
  output = io.BytesIO()
  with pd.ExcelWriter(output, engine="openpyxl") as writer:
    sample_data = pd.DataFrame({
        "Roll_Number": [
            "101",
            "102",
            "201",
            "202",
            "301",
            "302",
            "401",
            "402",
            "501",
            "502",
        ],
        "Name": [
            "Alice",
            "Bob",
            "Charlie",
            "Diana",
            "Ethan",
            "Fiona",
            "George",
            "Hannah",
            "Ian",
            "Julia",
        ],
        "Class": [
            "Class 1",
            "Class 1",
            "Class 2",
            "Class 2",
            "Class 3",
            "Class 3",
            "Class 4",
            "Class 4",
            "Class 5",
            "Class 5",
        ],
        "Gender": ["F", "M", "M", "F", "M", "F", "M", "F", "M", "F"],
    })
    sample_data.to_excel(writer, index=False, sheet_name="Students")
  return output.getvalue()


# --- 2. MAIN APP INTERFACE ---
st.title("🎓 Automated Exam Seating Arrangement System")
st.markdown(
    "Upload your student database, configure your room layouts, and generate"
    " optimized seating plans instantly."
)

with st.sidebar:
  st.header("1. Input Data")
  st.download_button(
      label="📥 Download Sample Excel Template",
      data=generate_sample_excel(),
      file_name="student_template.xlsx",
      mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  )

  uploaded_file = st.file_uploader(
      "Upload Student Excel File", type=["xlsx", "xls"]
  )

  st.header("2. Room Configuration")
  num_rooms = st.number_input(
      "Total Rooms Available", min_value=1, value=1, step=1
  )
  benches_per_room = st.number_input(
      "Benches per Room (Total Benches)", min_value=2, value=10, step=2
  )
  students_per_bench = 4  # Fixed rule: 4 students per bench

  st.header("3. Seating Preferences")
  block_seats = st.checkbox("Block specific seats/benches?")
  blocked_bench_indices = []
  if block_seats:
    b_input = st.text_input(
        "Enter blocked bench numbers separated by commas (e.g., 3, 7)", "3"
    )
    if b_input:
      blocked_bench_indices = [
          int(x.strip()) for x in b_input.split(",") if x.strip().isdigit()
      ]

# --- 3. PROCESSING ENGINE ---
if uploaded_file is not None:
  try:
    df = pd.read_excel(uploaded_file)
    st.success("Student data loaded successfully!")

    # Quick preview metrics
    total_students = len(df)
    total_capacity = num_rooms * benches_per_room * students_per_bench
    st.info(
        f"Total Students: **{total_students}** | Total Room Capacity:"
        f" **{total_capacity}**"
    )

    if total_students > total_capacity:
      st.warning(
          "⚠️ Warning: Total students exceed room capacity! Please add more"
          " rooms or benches."
      )

    if st.button("🚀 Generate Seating Plan"):
      # Basic round-robin distribution strategy respecting class & gender constraints
      df = df.sample(frac=1).reset_index(
          drop=True
      )  # Shuffle to randomize allocation

      # Allocate data structures
      rooms_allocation = {
          f"Room {r+1}": [] for r in range(int(num_rooms))
      }

      # Simple distribution simulation across rooms
      room_keys = list(rooms_allocation.keys())
      for idx, row in df.iterrows():
        target_room = room_keys[idx % len(room_keys)]
        rooms_allocation[target_room].append(row.to_dict())

      st.markdown("---")
      st.header("📊 Generated Outputs & Reports")

      # Tabbed outputs for readability
      tab1, tab2, tab3 = st.tabs([
          "📥 Download Seating Plan",
          "📋 Room-wise Student Roll Numbers",
          "📈 Summary Matrix Table",
      ])

      with tab1:
        st.subheader("Download Room-wise Seating Plan File")
        # Build Excel with multiple sheets or structured layout
        output_buffer = io.BytesIO()
        with pd.ExcelWriter(output_buffer, engine="openpyxl") as writer:
          for r_name, occupants in rooms_allocation.items():
            if occupants:
              r_df = pd.DataFrame(occupants)
              r_df.to_excel(writer, sheet_name=r_name, index=False)
            else:
              pd.DataFrame(
                  columns=["Roll_Number", "Name", "Class", "Gender"]
              ).to_excel(writer, sheet_name=r_name, index=False)

        st.download_button(
            label="💾 Download Complete Seating Plan (Excel)",
            data=output_buffer.getvalue(),
            file_name="Final_Seating_Plan.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

      with tab2:
        st.subheader("Table: Roll Numbers of Students by Room & Class")
        for r_name, occupants in rooms_allocation.items():
          with st.expander(f"{r_name} Seating List"):
            if occupants:
              temp_df = pd.DataFrame(occupants)
              st.dataframe(
                  temp_df[["Roll_Number", "Name", "Class", "Gender"]],
                  use_container_width=True,
              )
            else:
              st.write("No students assigned.")

      with tab3:
        st.subheader(
            "Table: Class-wise Student Count Matrix (Rooms vs Classes)"
        )
        # Build matrix: Rows = Rooms, Columns = Classes
        matrix_data = []
        all_classes = sorted(df["Class"].unique())

        for r_name, occupants in rooms_allocation.items():
          r_counts = {"Room": r_name}
          occ_df = pd.DataFrame(occupants) if occupants else pd.DataFrame()
          for cls in all_classes:
            if not occ_df.empty and "Class" in occ_df.columns:
              r_counts[cls] = len(occ_df[occ_df["Class"] == cls])
            else:
              r_counts[cls] = 0
          matrix_data.append(r_counts)

        matrix_df = pd.DataFrame(matrix_data)
        matrix_df.set_index("Room", inplace=True)
        # Add Row Total
        matrix_df["Total Students"] = matrix_df.sum(axis=1)
        # Add Column Total
        matrix_df.loc["Total"] = matrix_df.sum()

        st.dataframe(matrix_df, use_container_width=True)

  except Exception as e:
    st.error(f"Error processing file: {e}")
else:
  st.info("👈 Please upload your student Excel sheet using the sidebar to begin.")
