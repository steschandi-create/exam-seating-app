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
    "Upload your student database, configure your rooms, and download exact"
    " structured reports matching your specifications."
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
      "Total Rooms Available", min_value=1, value=2, step=1
  )
  benches_per_room = st.number_input(
      "Benches per Room (Total Benches)", min_value=2, value=10, step=2
  )
  students_per_bench = 4  # Fixed rule: 4 students per bench

  st.header("3. Seating Constraints")
  block_seats = st.checkbox("Block specific benches permanently?")
  blocked_bench_indices = []
  if block_seats:
    b_input = st.text_input(
        "Enter blocked bench numbers separated by commas (e.g., 3, 7)", "3"
    )
    if b_input:
      blocked_bench_indices = [
          int(x.strip()) for x in b_input.split(",") if x.strip().isdigit()
      ]

# --- 3. SEATING ALLOCATION ENGINE ---
if uploaded_file is not None:
  try:
    df = pd.read_excel(uploaded_file)
    st.success("Student data loaded successfully!")

    total_students = len(df)
    total_capacity = num_rooms * benches_per_room * students_per_bench
    st.info(
        f"Total Students: **{total_students}** | Total Room Seating Capacity:"
        f" **{total_capacity}**"
    )

    if total_students > total_capacity:
      st.warning(
          "⚠️ Warning: Total students exceed room capacity! Please add more"
          " rooms or increase benches."
      )

    if st.button("🚀 Generate Required Seating Plans"):
      # Shuffle data to randomize distribution while maintaining constraints
      df = df.sample(frac=1).reset_index(drop=True)

      # Distribute students evenly across available rooms round-robin style
      rooms_allocation = {f"Room {r+1}": [] for r in range(int(num_rooms))}
      room_keys = list(rooms_allocation.keys())

      for idx, row in df.iterrows():
        target_room = room_keys[idx % len(room_keys)]
        rooms_allocation[target_room].append(row.to_dict())

      st.markdown("---")
      st.header("📊 Generated System Reports")

      # --- BUILD MATRIX SUMMARY ---
      all_classes = sorted(df["Class"].unique())
      matrix_data = []

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
      # Row & Column Totals
      matrix_df["Total Students"] = matrix_df.sum(axis=1)
      matrix_df.loc["Total"] = matrix_df.sum()

      # --- DISPLAY TABS ON WEB PAGE ---
      tab1, tab2, tab3 = st.tabs([
          "📥 1. Downloadable Excel Package",
          "📋 2. Room-wise Roll Number Tables",
          "📈 3. Summary Matrix Table",
      ])

      with tab1:
        st.subheader("Download Complete Excel File")
        st.markdown(
            "The downloadable Excel file contains **separate sheets** for each"
            " requirement:"
        )
        st.markdown(
            "- **Room Seating Plans**: Detailed mapping layout of benches &"
            " rows."
        )
        st.markdown(
            "- **Class Roll Numbers**: Segmented roll numbers per class per"
            " room."
        )
        st.markdown(
            "- **Summary Matrix**: Room vs Class breakdown complete with row"
            " and column totals."
        )

        # Generate multi-tab workbook
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
          # Sheet 1: Summary Matrix
          matrix_df.to_excel(writer, sheet_name="Summary Matrix")

          # Sheet 2 & Onwards: Room-wise details
          for r_name, occupants in rooms_allocation.items():
            if occupants:
              r_df = pd.DataFrame(occupants)
              # Create structured seating presentation
              r_df.insert(0, "Bench_No", [f"Bench {(i//4)+1}" for i in range(len(r_df))])
              r_df.insert(1, "Side", ["Left" if ((i//4)%2)==0 else "Right" for i in range(len(r_df))])
              r_df.to_excel(writer, sheet_name=f"{r_name} Seating", index=False)
            else:
              empty_df = pd.DataFrame(
                  columns=[
                      "Bench_No",
                      "Side",
                      "Roll_Number",
                      "Name",
                      "Class",
                      "Gender",
                  ]
              )
              empty_df.to_excel(
                  writer, sheet_name=f"{r_name} Seating", index=False
              )

        st.download_button(
            label="💾 Download Comprehensive Seating Package (.xlsx)",
            data=excel_buffer.getvalue(),
            file_name="Master_Exam_Seating_Plan.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

      with tab2:
        st.subheader(
            "Table 2: Roll Numbers of Students From Each Class in Each Room"
        )
        for r_name, occupants in rooms_allocation.items():
          with st.expander(f"📂 {r_name} Breakdown"):
            if occupants:
              occ_df = pd.DataFrame(occupants)
              # Group by class to show roll lists clearly
              for cls_name, group in occ_df.groupby("Class"):
                st.markdown(f"**{cls_name}** ({len(group)} Students):")
                st.write(
                    ", ".join(
                        str(r) for r in group["Roll_Number"].tolist()
                    )
                )
            else:
              st.write("No students assigned.")

      with tab3:
        st.subheader(
            "Table 3: Room Headers & Number of Students with Totals Matrix"
        )
        st.dataframe(matrix_df, use_container_width=True)

  except Exception as e:
    st.error(f"Error reading or processing the file: {e}")
else:
  st.info("👈 Please upload your student database template using the sidebar.")
