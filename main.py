app.post('/exit_confirmed', async (req, res) => {
  try {
    const { order_id } = req.body;

    const trade = await prisma.trade.findFirst({
      where: { order_id },
    });

    if (!trade) {
      return res.status(404).json({ error: 'Trade not found' });
    }

    // Actualiza el trade con ese order_id
    const updatedTrade = await prisma.trade.update({
      where: { order_id },
      data: { exit_confirmed: true },
    });

    // También actualiza todos los demás trades con mismo símbolo y exit_confirmed false
    await prisma.trade.updateMany({
      where: {
        symbol: trade.symbol,
        exit_confirmed: false,
        NOT: { order_id }, // evitar actualizar el mismo trade
      },
      data: { exit_confirmed: true },
    });

    res.status(200).json(updatedTrade);
  } catch (error) {
    console.error('❌ Error en /exit_confirmed:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});
