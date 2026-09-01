import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes
)

from excel import add_transaction

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Halo Farhan 👋\n\n"
        "💰 Finance Bot aktif!\n\n"
        "Contoh pencatatan:\n"
        "/makan 25000 makan siang\n"
        "/bensin 50000 isi bensin\n"
    )


async def makan(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not context.args:
        await update.message.reply_text(
            "Format yang benar:\n"
            "/makan 25000 makan siang"
        )
        return

    try:
        nominal = int(context.args[0])
    except ValueError:
        await update.message.reply_text(
            "Nominal harus berupa angka.\n"
            "Contoh: /makan 25000"
        )
        return

    keterangan = " ".join(context.args[1:])

    transaction_id, tanggal = add_transaction(
        jenis="Pengeluaran",
        kategori="Makan",
        nominal=nominal,
        keterangan=keterangan
    )

    await update.message.reply_text(
        f"✅ TRANSAKSI TERCATAT\n\n"
        f"ID: {transaction_id}\n"
        f"Kategori: Makan\n"
        f"Nominal: Rp{nominal:,}\n"
        f"Keterangan: {keterangan or '-'}"
    )


async def bensin(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not context.args:
        await update.message.reply_text(
            "Format yang benar:\n"
            "/bensin 50000 isi bensin"
        )
        return

    try:
        nominal = int(context.args[0])
    except ValueError:
        await update.message.reply_text(
            "Nominal harus berupa angka.\n"
            "Contoh: /bensin 50000"
        )
        return

    keterangan = " ".join(context.args[1:])

    transaction_id, tanggal = add_transaction(
        jenis="Pengeluaran",
        kategori="Bensin",
        nominal=nominal,
        keterangan=keterangan
    )

    await update.message.reply_text(
        f"✅ TRANSAKSI TERCATAT\n\n"
        f"ID: {transaction_id}\n"
        f"Kategori: Bensin\n"
        f"Nominal: Rp{nominal:,}\n"
        f"Keterangan: {keterangan or '-'}"
    )


def main():

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("makan", makan))
    app.add_handler(CommandHandler("bensin", bensin))

    print("Finance Bot berjalan...")

    app.run_polling()


if __name__ == "__main__":
    main()