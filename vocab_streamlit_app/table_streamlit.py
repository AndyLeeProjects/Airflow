from st_aggrid import GridOptionsBuilder, AgGrid, GridUpdateMode, DataReturnMode, ColumnsAutoSizeMode
import pandas as pd


def interactive_table(data, key):

    gb = GridOptionsBuilder.from_dataframe(data)
    gb.configure_pagination(paginationAutoPageSize=True, enabled=True)  # Add pagination

    gb.configure_side_bar()  # Add a sidebar
    # gb.configure_selection(selection_mode="multiple", use_checkbox=True)
    gridOptions = gb.build()

    grid_response = AgGrid(
        data,
        gridOptions=gridOptions,
        data_return_mode="FILTERED_AND_SORTED",
        update_mode="MODEL_CHANGED",
        fit_columns_on_grid_load=False,
        enable_enterprise_modules=True,
        height=500,
        width="100%", 
        key = key,
        columns_auto_size_mode=ColumnsAutoSizeMode.FIT_CONTENTS,
        editable=True,
        stop_enter_editing=True,
        # reload_data=True
    )

    data = grid_response["data"]
    # selected = grid_response['selected_rows']
    df = pd.DataFrame(data)  # Pass the selected rows to a new dataframe df

    return df


