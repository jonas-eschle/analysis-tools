#include <cmath>
#include <cassert>

#include "Roo3DPolynomial.h"
#include "RooAbsReal.h"
#include "RooArgList.h"
#include "RooMsgService.h"

#include "TError.h"

using namespace std;

ClassImp(Roo3DPolynomial)
;

////////////////////////////////////////////////////////////////////////////////
/// coverity[UNINIT_CTOR]

Roo3DPolynomial::Roo3DPolynomial()
{
}


////////////////////////////////////////////////////////////////////////////////
/// Constructor

Roo3DPolynomial::Roo3DPolynomial(const char* name, const char* title,
              RooAbsReal& x, RooAbsReal& y, RooAbsReal& z,
              const RooArgList& coefListX,
              const RooArgList& coefListY,
              const RooArgList& coefListZ,
              Int_t lowestOrder) :
  RooAbsPdf(name, title),
  _x("x", "x dependent", this, x),
  _y("y", "y dependent", this, y),
  _z("z", "z dependent", this, z),
  _coefListX("coefListX","List of x coefficients",this),
  _coefListY("coefListY","List of y coefficients",this),
  _coefListZ("coefListZ","List of z coefficients",this),
  _lowestOrder(lowestOrder)
{
  // Check lowest order
  if (_lowestOrder<0) {
    coutE(InputArguments) << "Roo3DPolynomial::ctor(" << GetName()
           << ") WARNING: lowestOrder must be >=0, setting value to 0" << endl ;
    _lowestOrder=0 ;
  }

  RooFIter coefIter = coefListX.fwdIterator() ;
  RooAbsArg* coef ;
  while((coef = (RooAbsArg*)coefIter.next())) {
    if (!dynamic_cast<RooAbsReal*>(coef)) {
      coutE(InputArguments) << "Roo3DPolynomial::ctor(" << GetName() << ") ERROR: coefficient " << coef->GetName()
             << " is not of type RooAbsReal" << endl ;
      R__ASSERT(0) ;
    }
    _coefListX.add(*coef) ;
  }

  coefIter = coefListY.fwdIterator() ;
  while((coef = (RooAbsArg*)coefIter.next())) {
    if (!dynamic_cast<RooAbsReal*>(coef)) {
      coutE(InputArguments) << "Roo3DPolynomial::ctor(" << GetName() << ") ERROR: coefficient " << coef->GetName()
             << " is not of type RooAbsReal" << endl ;
      R__ASSERT(0) ;
    }
    _coefListY.add(*coef) ;
  }

  coefIter = coefListZ.fwdIterator() ;
  while((coef = (RooAbsArg*)coefIter.next())) {
    if (!dynamic_cast<RooAbsReal*>(coef)) {
      coutE(InputArguments) << "Roo3DPolynomial::ctor(" << GetName() << ") ERROR: coefficient " << coef->GetName()
             << " is not of type RooAbsReal" << endl ;
      R__ASSERT(0) ;
    }
    _coefListZ.add(*coef) ;
  }
}



////////////////////////////////////////////////////////////////////////////////

Roo3DPolynomial::Roo3DPolynomial(const char* name, const char* title,
                           RooAbsReal& x, RooAbsReal& y, RooAbsReal& z) :
  RooAbsPdf(name, title),
  _x("x", "x dependent", this, x),
  _y("y", "y dependent", this, y),
  _z("z", "z dependent", this, z),
  _coefListX("coefListX","List of x coefficients",this),
  _coefListY("coefListY","List of y coefficients",this),
  _coefListZ("coefListZ","List of z coefficients",this),
  _lowestOrder(1)
{ }

////////////////////////////////////////////////////////////////////////////////
/// Copy constructor

Roo3DPolynomial::Roo3DPolynomial(const Roo3DPolynomial& other, const char* name) :
  RooAbsPdf(other, name),
  _x("x", "x dependent", this, other._x),
  _y("y", "y dependent", this, other._y),
  _z("z", "z dependent", this, other._z),
  _coefListX("coefListX",this, other._coefListX),
  _coefListY("coefListY",this, other._coefListY),
  _coefListZ("coefListZ",this, other._coefListZ),
  _lowestOrder(other._lowestOrder)
{ }




////////////////////////////////////////////////////////////////////////////////
/// Destructor

Roo3DPolynomial::~Roo3DPolynomial()
{ }




////////////////////////////////////////////////////////////////////////////////

Double_t Roo3DPolynomial::evaluate() const
{
  // Calculate and return value of polynomial

  const int lowestOrder = _lowestOrder;
  Double_t retValX, retValY, retValZ ;
  // Common objects
  const RooArgSet* nset;
  RooFIter it;
  RooAbsReal* c;
  unsigned sz;
  // x
  sz = _coefListX.getSize();
  if (sz) {
    _wksp.clear();
    _wksp.reserve(sz);
    {
      nset = _coefListX.nset();
      it = _coefListX.fwdIterator();
      while ((c = (RooAbsReal*) it.next())) _wksp.push_back(c->getVal(nset));
    }
    const Double_t x = _x;
    retValX = _wksp[sz - 1];
    for (unsigned i = sz - 1; i--; ) retValX = _wksp[i] + x * retValX;
    retValX *= std::pow(x, lowestOrder);
  }
  // y
  sz = _coefListY.getSize();
  if (sz) {
    _wksp.clear();
    _wksp.reserve(sz);
    {
      nset = _coefListY.nset();
      it = _coefListY.fwdIterator();
      while ((c = (RooAbsReal*) it.next())) _wksp.push_back(c->getVal(nset));
    }
    const Double_t y = _y;
    retValY = _wksp[sz - 1];
    for (unsigned i = sz - 1; i--; ) retValY = _wksp[i] + y * retValY;
    retValY *= std::pow(y, lowestOrder);
  }
  // z
  sz = _coefListZ.getSize();
  if (sz) {
    _wksp.clear();
    _wksp.reserve(sz);
    {
      nset = _coefListZ.nset();
      it = _coefListZ.fwdIterator();
      while ((c = (RooAbsReal*) it.next())) _wksp.push_back(c->getVal(nset));
    }
    const Double_t z = _z;
    retValZ = _wksp[sz - 1];
    for (unsigned i = sz - 1; i--; ) retValZ = _wksp[i] + z * retValZ;
    retValZ *= std::pow(z, lowestOrder);
  }
  // Final power
  return retValX + retValY + retValZ + (lowestOrder ? 1. : 0.);
}



////////////////////////////////////////////////////////////////////////////////

Int_t Roo3DPolynomial::getAnalyticalIntegral(RooArgSet& allVars, RooArgSet& analVars, const char* /*rangeName*/) const
{
  if (matchArgs(allVars, analVars, _x)) return ROO_3DPOLYNOMIAL_XCODE;
  if (matchArgs(allVars, analVars, _y)) return ROO_3DPOLYNOMIAL_YCODE;
  if (matchArgs(allVars, analVars, _z)) return ROO_3DPOLYNOMIAL_ZCODE;
  if (matchArgs(allVars, analVars, _x, _y)) return ROO_3DPOLYNOMIAL_XCODE*ROO_3DPOLYNOMIAL_YCODE;
  if (matchArgs(allVars, analVars, _x, _z)) return ROO_3DPOLYNOMIAL_XCODE*ROO_3DPOLYNOMIAL_ZCODE;
  if (matchArgs(allVars, analVars, _y, _z)) return ROO_3DPOLYNOMIAL_YCODE*ROO_3DPOLYNOMIAL_ZCODE;
  if (matchArgs(allVars, analVars, _x, _y, _z)) return ROO_3DPOLYNOMIAL_XCODE*ROO_3DPOLYNOMIAL_YCODE*ROO_3DPOLYNOMIAL_ZCODE;
  return 0;
}



////////////////////////////////////////////////////////////////////////////////

Double_t Roo3DPolynomial::analyticalIntegral(Int_t code, const char* rangeName) const
{
  R__ASSERT(code>0) ;

  const Double_t xmin = _x.min(rangeName), xmax = _x.max(rangeName);
  const Double_t ymin = _y.min(rangeName), ymax = _y.max(rangeName);
  const Double_t zmin = _z.min(rangeName), zmax = _z.max(rangeName);
  const int lowestOrder = _lowestOrder;
  unsigned sz;
  // Common vars
  const RooArgSet* nset;
  RooFIter it;
  Double_t retValX, retValY, retValZ = 0.0;
  // x
  sz = _coefListX.getSize();
  if (sz) {
    _wksp.clear();
    _wksp.reserve(sz);
    {
      nset = _coefListX.nset();
      it = _coefListX.fwdIterator();
      RooAbsReal* c;
      unsigned i = 1 + lowestOrder;
      while ((c = (RooAbsReal*) it.next())) {
        _wksp.push_back(c->getVal(nset) / Double_t(i));
        ++i;
      }
    }
    Double_t minX = _wksp[sz - 1], maxX = _wksp[sz - 1];
    for (unsigned i = sz - 1; i--; )
      minX = _wksp[i] + xmin * minX, maxX = _wksp[i] + xmax * maxX;
    retValX = maxX * std::pow(xmax, 1 + lowestOrder) - minX * std::pow(xmin, 1 + lowestOrder);
    if (code % ROO_3DPOLYNOMIAL_YCODE == 0) retValX *= (ymax - ymin);
    if (code % ROO_3DPOLYNOMIAL_ZCODE == 0) retValX *= (zmax - zmin);
  }
  // y
  sz = _coefListY.getSize();
  if (sz) {
    _wksp.clear();
    _wksp.reserve(sz);
    {
      nset = _coefListY.nset();
      it = _coefListY.fwdIterator();
      RooAbsReal* c;
      unsigned i = 1 + lowestOrder;
      while ((c = (RooAbsReal*) it.next())) {
        _wksp.push_back(c->getVal(nset) / Double_t(i));
        ++i;
      }
    }
    Double_t minY = _wksp[sz - 1], maxY = _wksp[sz - 1];
    for (unsigned i = sz - 1; i--; )
      minY = _wksp[i] + ymin * minY, maxY = _wksp[i] + ymax * maxY;
    retValY = maxY * std::pow(ymax, 1 + lowestOrder) - minY * std::pow(ymin, 1 + lowestOrder);
    if (code % ROO_3DPOLYNOMIAL_XCODE == 0) retValY *= (xmax - xmin);
    if (code % ROO_3DPOLYNOMIAL_ZCODE == 0) retValY *= (zmax - zmin);
  }
  // z
  sz = _coefListZ.getSize();
  if (sz) {
    _wksp.clear();
    _wksp.reserve(sz);
    {
      nset = _coefListZ.nset();
      it = _coefListZ.fwdIterator();
      RooAbsReal* c;
      unsigned i = 1 + lowestOrder;
      while ((c = (RooAbsReal*) it.next())) {
        _wksp.push_back(c->getVal(nset) / Double_t(i));
        ++i;
      }
    }
    Double_t minZ = _wksp[sz - 1], maxZ = _wksp[sz - 1];
    for (unsigned i = sz - 1; i--; )
      minZ = _wksp[i] + zmin * minZ, maxZ = _wksp[i] + zmax * maxZ;
    retValZ = maxZ * std::pow(zmax, 1 + lowestOrder) - minZ * std::pow(zmin, 1 + lowestOrder);
    if (code % ROO_3DPOLYNOMIAL_XCODE == 0) retValZ *= (xmax - xmin);
    if (code % ROO_3DPOLYNOMIAL_YCODE == 0) retValZ *= (ymax - ymin);
  }
  Double_t constTerm = (lowestOrder ? 1.0 : 0.0);
  if (lowestOrder) {
    if (code % ROO_3DPOLYNOMIAL_XCODE) constTerm *= (xmax - xmin);
    if (code % ROO_3DPOLYNOMIAL_YCODE) constTerm *= (ymax - ymin);
    if (code % ROO_3DPOLYNOMIAL_ZCODE) constTerm *= (zmax - zmin);
  }
  return retValX + retValY + retValZ + constTerm ;
}

