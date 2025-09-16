import pandas as pd
import random

def read_csv_to_df(file_path):
    df = pd.read_csv(file_path)
    return df

def add_iin_and_phone(df):
    def generate_iin():
        return ''.join([str(random.randint(0, 9)) for _ in range(12)])

    def generate_phone():
        prefix = random.choice(['700', '707', '705', '775'])
        number = ''.join([str(random.randint(0, 9)) for _ in range(7)])
        return f'+7({prefix}){number}'

    df['IIN'] = [generate_iin() for _ in range(len(df))]
    df['phoneNum'] = [generate_phone() for _ in range(len(df))]
    cols = list(df.columns)
    cols.remove('IIN')
    cols.remove('phoneNum')
    customer_idx = cols.index('client_code')
    cols.insert(customer_idx + 1, 'IIN')
    cols.insert(customer_idx + 2, 'phoneNum')
    df = df[cols]
    return df


def save_df_to_csv(df, file_path, index=False):
    import os
    directory = os.path.dirname(file_path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    df.to_csv(file_path, index=index)


df = read_csv_to_df('data/clients.csv')
df = add_iin_and_phone(df)
save_df_to_csv(df, 'data/clients_enriched.csv', index=False)
print('Saved enriched DataFrame to data/clients_enriched.csv')